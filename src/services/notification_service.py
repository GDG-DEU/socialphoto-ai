import socketio
import logging
import httpx
from typing import Dict, Any, Union, List

from src.config import get_settings
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Socket.IO tabanlı bildirim servisi.
    Backend'e job completion/failure bildirimleri gönderir.
    """
    
    def __init__(self, cors_allowed_origins: Union[str, List[str]] = "*"):
        settings = get_settings()
        self.socket_io_secret = settings.socket_io_secret
        if not self.socket_io_secret:
            logger.warning("SOCKET_IO_SECRET not configured! Socket.IO connections will be rejected.")

        self.api_key = settings.api_key
        if not self.api_key:
            logger.error("API_KEY not configured! HTTP webhook notifications will be skipped.")
        
        self.sio = socketio.AsyncServer(
            async_mode='asgi', 
            cors_allowed_origins=cors_allowed_origins
        )
        self._setup_events()
    
    def _setup_events(self):
        """Socket.IO event handler'larını ayarla"""
        
        @self.sio.event
        async def connect(sid, environ, auth):
            """
            Socket.IO bağlantı handler'ı.
            Auth token'ı kontrol eder ve geçersizse bağlantıyı reddeder.
            
            Args:
                sid: Session ID
                environ: ASGI environ dict
                auth: Authentication data from client (dict with 'token' key expected)
            """
            # Check if SOCKET_IO_SECRET is configured
            if not self.socket_io_secret:
                logger.error(f"Connection rejected from {sid}: SOCKET_IO_SECRET not configured")
                return False
            
            # Verify auth token
            if not auth or not isinstance(auth, dict):
                logger.warning(f"Connection rejected from {sid}: No auth data provided")
                return False
            
            token = auth.get("token")
            if not token:
                logger.warning(f"Connection rejected from {sid}: No token in auth data")
                return False
            
            if token != self.socket_io_secret:
                logger.warning(f"Connection rejected from {sid}: Invalid token")
                return False
            
            logger.info(f"Client connected: {sid} (authenticated)")
            return True
        
        @self.sio.event
        async def disconnect(sid):
            logger.info(f"Client disconnected: {sid}")
    
    async def notify_job_completion(self, job_data: Dict[str, Any]):
        """
        İş tamamlandığında backend'e hem Socket.IO hem de HTTP Webhook üzerinden bildirim gönder.
        """
        # 1. Mevcut Socket.IO yayını (Eğer frontend vs. dinliyorsa diye bozmayalım)
        # webhook_url sadece backend webhook çağrısı için kullanılmalı, Socket.IO istemcilerine yayınlanmamalı
        socket_payload = {key: value for key, value in job_data.items() if key != "webhook_url"}
        await self.sio.emit("job_done", socket_payload)
        
        # 2. YENİ EKLENEN: Backend'e HTTP POST (Webhook) atma kısmı
        webhook_url = job_data.get("webhook_url")
        if webhook_url:
            if not self.api_key:
                logger.error(f"Cannot send HTTP webhook to {webhook_url}: API_KEY not configured")
                return

            try:
                headers = {"x-api-key": self.api_key}
                
                # httpx ile backend'e asenkron POST isteği atıyoruz
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook_url, 
                        json=job_data, 
                        headers=headers,
                        timeout=10.0
                    )
                    response.raise_for_status() # Hata varsa (404, 500) except bloğuna düşürür
                    logger.info(f"Webhook successfully sent to backend! Status: {response.status_code}")
            except Exception as e:
                logger.error(f"Failed to send HTTP webhook to {webhook_url}. Error: {str(e)}")
        else:
            logger.debug("No webhook_url found in job_data; skipping HTTP notification.")
    
    def get_asgi_app(self, fastapi_app):
        """
        Socket.IO ve FastAPI uygulamalarını birleştir.
        
        Args:
            fastapi_app: FastAPI uygulama instance'ı
            
        Returns:
            Combined ASGI application
        """
        return socketio.ASGIApp(self.sio, other_asgi_app=fastapi_app)


input_origins = get_settings().cors_allowed_origins
allowed_origins: Union[str, List[str]] = input_origins

if input_origins != "*":
    allowed_origins = [origin.strip() for origin in input_origins.split(",")]

notification_service = NotificationService(cors_allowed_origins=allowed_origins)

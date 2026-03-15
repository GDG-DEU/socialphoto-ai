import socketio
import logging
import os
import httpx
from typing import Dict, Any, Union, List
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Socket.IO tabanlı bildirim servisi.
    Backend'e job completion/failure bildirimleri gönderir.
    """
    
    def __init__(self, cors_allowed_origins: Union[str, List[str]] = "*"):
        self.socket_io_secret = os.getenv("SOCKET_IO_SECRET")
        if not self.socket_io_secret:
            logger.warning("SOCKET_IO_SECRET not configured! Socket.IO connections will be rejected.")
        
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
        await self.sio.emit("job_done", job_data)
        
        # 2. YENİ EKLENEN: Backend'e HTTP POST (Webhook) atma kısmı
        webhook_url = job_data.get("webhook_url")
        if webhook_url:
            try:
                # Backend için API Anahtarı
                api_key = os.getenv("X-API-Key", "tpCPZBaFflXj-LnzUO3kXwuWmlvN6kfTLJjgCz1yvX4")
                headers = {"x-api-key": api_key}
                
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
            logger.warning("No webhook_url found in job_data! Cannot send HTTP notification.")
    
    def get_asgi_app(self, fastapi_app):
        """
        Socket.IO ve FastAPI uygulamalarını birleştir.
        
        Args:
            fastapi_app: FastAPI uygulama instance'ı
            
        Returns:
            Combined ASGI application
        """
        return socketio.ASGIApp(self.sio, other_asgi_app=fastapi_app)


input_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
allowed_origins: Union[str, List[str]] = input_origins

if input_origins != "*":
    allowed_origins = [origin.strip() for origin in input_origins.split(",")]

notification_service = NotificationService(cors_allowed_origins=allowed_origins)

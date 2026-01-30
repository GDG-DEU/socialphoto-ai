import socketio
import logging
import os
from typing import Dict, Any, Union, List

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
        İş tamamlandığında backend'e bildirim gönder.
        
        TODO: Şuanda tüm clientlara gönderiyor, 
        daha sonra sadece ilgili backend'e gönderecek şekilde değiştirilecek
        (room-based messaging veya sid tracking ile)
        
        Args:
            job_data: Job bilgileri (job_id, status, result, error vb.)
        """
        await self.sio.emit("job_done", job_data)
        logger.info(f"Job completion notification sent: {job_data.get('job_id')}")
    
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

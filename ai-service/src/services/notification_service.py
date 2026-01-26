import socketio
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Socket.IO tabanlı bildirim servisi.
    Backend'e job completion/failure bildirimleri gönderir.
    """
    
    def __init__(self, cors_allowed_origins: str = "*"):
        self.sio = socketio.AsyncServer(
            async_mode='asgi', 
            cors_allowed_origins=cors_allowed_origins
        )
        self._setup_events()
    
    def _setup_events(self):
        """Socket.IO event handler'larını ayarla"""
        
        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"Client connected: {sid}")
        
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


# Global instance
notification_service = NotificationService()

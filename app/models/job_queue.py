from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime, timedelta, UTC

class JobQueue(Base):
    __tablename__ = "job_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # CONFIGURACIÓN DEL JOB
    queue_name = Column(String(100), nullable=False, index=True)  # "email_import", "email_parsing", "transaction_parsing"
    job_type = Column(String(100), nullable=False)  # Tipo específico del job
    job_data = Column(JSON, nullable=False)  # Datos del job (ID, parámetros, etc.)
    
    # CONTROL DE WORKERS
    status = Column(String(50), nullable=False, index=True, default="pending")  # pending, processing, completed, failed, expired
    worker_id = Column(String(100), nullable=True, index=True)  # ID del worker que está procesando
    
    # TIMESTAMPS
    created_at = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    scheduled_at = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)  # Cuándo debe ejecutarse
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Timeout para workers colgados
    
    # CONTROL DE ERRORES
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    error_message = Column(Text, nullable=True)
    
    # RESULTADOS
    result_data = Column(JSON, nullable=True)  # Resultados del job procesado
    
    # PRIORIDAD
    priority = Column(Integer, nullable=False, index=True, default=100)  # Menor número = mayor prioridad
    
    def __repr__(self):
        return f"<JobQueue(queue={self.queue_name}, type={self.job_type}, status={self.status})>"
    
    @property
    def is_expired(self):
        """Verifica si el job ha expirado"""
        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return True
        return False
    
    @property
    def can_retry(self):
        """Verifica si el job puede ser reintentado"""
        return self.attempts < self.max_attempts
    
    def set_timeout(self, minutes: int = 30):
        """Establece el timeout del job"""
        self.expires_at = datetime.now(UTC) + timedelta(minutes=minutes) 
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class EmailImportJob(Base):
    __tablename__ = "email_import_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)
    
    # CONTROL DE WORKERS Y ESTADO
    status = Column(String(50), default="waiting", nullable=False, index=True)  # waiting, queued, running, completed, error, suspended
    worker_id = Column(String(100), nullable=True)  # ID del worker que está procesando
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    timeout_at = Column(DateTime, nullable=True)  # Para detectar workers colgados
    
    # SCHEDULING Y FRECUENCIA
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True, index=True)  # Para que el worker detecte eficientemente cuándo debe ejecutarse
    
    # ESTADÍSTICAS DE EJECUCIÓN
    total_runs = Column(Integer, default=0, nullable=False)
    total_emails_processed = Column(Integer, default=0, nullable=False)
    emails_processed_last_run = Column(Integer, default=0, nullable=False)
    emails_found_last_run = Column(Integer, default=0, nullable=False)
    last_run_duration_seconds = Column(Integer, nullable=True)
    
    # CONTROL DE ERRORES
    consecutive_errors = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    last_error_message = Column(Text, nullable=True)
    
    # HISTORIAL Y AUDITORÍA
    run_history = Column(JSON, nullable=True)  # Lista de últimos 10 runs con detalles
    
    # SINCRONIZACIÓN INCREMENTAL
    last_message_id = Column(String(255), nullable=True)  # Para sincronización incremental
    
    # TIMESTAMPS GENERALES
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    integration = relationship("Integration", back_populates="import_jobs")
    parsing_jobs = relationship("EmailParsingJob", back_populates="import_job", cascade="all, delete-orphan") 
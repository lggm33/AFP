from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class EmailParsingJob(Base):
    __tablename__ = "email_parsing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    email_import_job_id = Column(Integer, ForeignKey("email_import_jobs.id"), nullable=False, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=True, index=True)
    
    # Datos del email
    email_message_id = Column(String(255), nullable=False, index=True)
    email_subject = Column(String(500), nullable=True)
    email_from = Column(String(255), nullable=True, index=True)
    email_body = Column(Text, nullable=True)  # Contenido raw para debugging
    
    # CONTROL DE WORKERS - Consistente con EmailImportJob
    status = Column(String(50), default="waiting", nullable=False, index=True)  # waiting, queued, running, completed, error, suspended
    worker_id = Column(String(100), nullable=True)  # ID del worker que está procesando
    timeout_at = Column(DateTime, nullable=True)  # Para detectar workers colgados
    
    # RESUMEN Y DETALLES DEL RESULTADO
    summary = Column(String(255), nullable=True)  # Resumen de lo que pasó: "transaction_created", "no_bank_identified", "no_transaction_found", etc.
    
    # PARSING Y RESULTADOS
    confidence_score = Column(Float, default=0.0, nullable=False)  # 0.0 - 1.0
    parsing_attempts = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=3, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # METADATOS DE PARSING (qué reglas se usaron, qué se extrajo)
    parsing_rules_used = Column(JSON, nullable=True)  # IDs de las reglas que se usaron
    extracted_data = Column(JSON, nullable=True)  # Datos extraídos antes de crear Transaction
    
    # Timestamps
    processed_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    import_job = relationship("EmailImportJob", back_populates="parsing_jobs")
    bank = relationship("Bank", back_populates="parsing_jobs")
    transactions = relationship("Transaction", back_populates="parsing_job", cascade="all, delete-orphan") 
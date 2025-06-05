from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class TransactionParsingJob(Base):
    __tablename__ = "transaction_parsing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, running, completed, failed
    emails_to_parse = Column(Integer, default=0, nullable=False)
    emails_parsed = Column(Integer, default=0, nullable=False)
    transactions_created = Column(Integer, default=0, nullable=False)
    errors_count = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Metadata adicional
    processing_batch_id = Column(String(50), nullable=True, index=True)  # Para agrupar procesamiento
    total_processing_time_seconds = Column(Integer, default=0, nullable=False)
    
    # Note: Este job no tiene relaciones directas - actúa sobre EmailParsingJob existentes
    # La relación es implícita a través del status de EmailParsingJob 
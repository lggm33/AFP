from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class EmailParsingJob(Base):
    __tablename__ = "email_parsing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    email_import_job_id = Column(Integer, ForeignKey("email_import_jobs.id"), nullable=False, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=True, index=True)
    email_message_id = Column(String(255), nullable=False, index=True)
    email_subject = Column(String(500), nullable=True)
    email_from = Column(String(255), nullable=True, index=True)
    email_body = Column(Text, nullable=True)  # Contenido raw para debugging
    parsing_status = Column(String(50), default="pending", nullable=False, index=True)  # pending, success, failed, manual_review
    confidence_score = Column(Float, default=0.0, nullable=False)  # 0.0 - 1.0
    parsing_attempts = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    import_job = relationship("EmailImportJob", back_populates="parsing_jobs")
    bank = relationship("Bank", back_populates="parsing_jobs")
    transactions = relationship("Transaction", back_populates="parsing_job", cascade="all, delete-orphan") 
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class EmailImportJob(Base):
    __tablename__ = "email_import_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, running, completed, failed
    emails_processed = Column(Integer, default=0, nullable=False)
    emails_found = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    last_message_id = Column(String(255), nullable=True)  # Para sincronización incremental
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    integration = relationship("Integration", back_populates="import_jobs")
    parsing_jobs = relationship("EmailParsingJob", back_populates="import_job", cascade="all, delete-orphan") 
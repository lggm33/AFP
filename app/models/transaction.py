from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Numeric, Text, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    description = Column(String(500), nullable=True)
    amount = Column(Float, nullable=False, index=True)
    date = Column(DateTime, nullable=True, index=True)
    source = Column(String(255), nullable=True)
    email_id = Column(String(255), nullable=True, index=True)  # Mantenemos por compatibilidad
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    from_bank = Column(String(255), nullable=True, index=True)
    to_bank = Column(String(255), nullable=True, index=True)
    
    # Nuevos campos para trazabilidad
    email_parsing_job_id = Column(Integer, ForeignKey("email_parsing_jobs.id"), nullable=True, index=True)
    confidence_score = Column(Float, default=0.0, nullable=False)  # 0.0 - 1.0
    verification_status = Column(String(50), default="auto", nullable=False, index=True)  # auto, manual_verified, disputed
    
    # Relaciones
    parsing_job = relationship("EmailParsingJob", back_populates="transactions") 
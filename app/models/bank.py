from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class Bank(Base):
    __tablename__ = "banks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)  # @bancolombia.com.co
    parsing_patterns = Column(Text, nullable=True)  # JSON con regex patterns (LEGACY - OBSOLETO)
    is_active = Column(Boolean, default=True, nullable=False)
    confidence_threshold = Column(Float, default=0.7, nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # NUEVOS CAMPOS para mejor identificación y matching
    sender_domains = Column(JSON, nullable=True)  # ["@bancobcr.com", "@baccr.fi.cr", "@mensajero.bancobcr.com"]
    sender_emails = Column(JSON, nullable=True)  # ["notificacion@notificacionesbaccr.com", "mensajero@bancobcr.com"]
    keywords = Column(JSON, nullable=True)  # ["transacción", "compra", "retiro", "transferencia"]
    parsing_priority = Column(Integer, default=0, nullable=False, index=True)  # Orden de matching (mayor = más prioridad)
    
    # Metadata del banco
    country_code = Column(String(2), default="CR", nullable=False, index=True)  # CR, CO, MX, etc
    bank_code = Column(String(10), nullable=True, index=True)  # Código oficial del banco
    bank_type = Column(String(50), default="commercial", nullable=False)  # commercial, cooperative, digital
    website = Column(String(255), nullable=True)  # https://www.bancobcr.com
    
    # Estadísticas de procesamiento
    emails_processed = Column(Integer, default=0, nullable=False)
    transactions_created = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)  # 0.0 - 1.0
    last_processed_at = Column(DateTime, nullable=True)
    
    # Relaciones
    parsing_jobs = relationship("EmailParsingJob", back_populates="bank")

    email_templates = relationship("BankEmailTemplate", back_populates="bank", cascade="all, delete-orphan") 
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.infrastructure.database.db import Base

class UserDB(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    integrations = relationship("IntegrationDB", back_populates="user", cascade="all, delete-orphan")

class IntegrationDB(Base):
    __tablename__ = "integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(50), default="gmail", nullable=False)
    email_account = Column(String(255), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    access_token = Column(Text, nullable=True)  # Puede ser largo, usar Text
    refresh_token = Column(Text, nullable=True)
    last_sync = Column(DateTime, nullable=True)
    sync_frequency_minutes = Column(Integer, default=5, nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    user = relationship("UserDB", back_populates="integrations")
    import_jobs = relationship("EmailImportJobDB", back_populates="integration", cascade="all, delete-orphan")

class BankDB(Base):
    __tablename__ = "banks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)  # @bancolombia.com.co
    parsing_patterns = Column(Text, nullable=True)  # JSON con regex patterns
    is_active = Column(Boolean, default=True, nullable=False)
    confidence_threshold = Column(Float, default=0.7, nullable=False)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    parsing_jobs = relationship("EmailParsingJobDB", back_populates="bank")

class EmailImportJobDB(Base):
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
    integration = relationship("IntegrationDB", back_populates="import_jobs")
    parsing_jobs = relationship("EmailParsingJobDB", back_populates="import_job", cascade="all, delete-orphan")

class EmailParsingJobDB(Base):
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
    import_job = relationship("EmailImportJobDB", back_populates="parsing_jobs")
    bank = relationship("BankDB", back_populates="parsing_jobs")
    transactions = relationship("TransactionDB", back_populates="parsing_job", cascade="all, delete-orphan")

class TransactionDB(Base):
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
    parsing_job = relationship("EmailParsingJobDB", back_populates="transactions")

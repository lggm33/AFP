from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Integration(Base):
    __tablename__ = "integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # CONFIGURACIÓN DE LA INTEGRACIÓN
    provider = Column(String(50), default="gmail", nullable=False)
    email_account = Column(String(255), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # CREDENCIALES OAUTH
    access_token = Column(Text, nullable=True)  # Puede ser largo, usar Text
    refresh_token = Column(Text, nullable=True)
    
    # CONFIGURACIÓN DE SINCRONIZACIÓN
    sync_frequency_minutes = Column(Integer, default=5, nullable=False)
    initial_lookback_days = Column(Integer, default=30, nullable=True)  # Days to look back when no processed emails
    
    # TIMESTAMPS DE CONFIGURACIÓN
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    
    # Relaciones
    user = relationship("User", back_populates="integrations")
    import_jobs = relationship("EmailImportJob", back_populates="integration", cascade="all, delete-orphan") 
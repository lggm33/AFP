from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Integration(Base):
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
    user = relationship("User", back_populates="integrations")
    import_jobs = relationship("EmailImportJob", back_populates="integration", cascade="all, delete-orphan") 
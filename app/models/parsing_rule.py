from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class ParsingRule(Base):
    __tablename__ = "parsing_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id"), nullable=False, index=True)
    rule_name = Column(String(255), nullable=False, index=True)  # "BCR Amount Pattern", "Scotiabank Date Pattern"
    rule_type = Column(String(50), nullable=False, index=True)  # amount, date, description, merchant, transaction_type
    regex_pattern = Column(Text, nullable=False)  # Patrón regex para extraer datos
    test_string = Column(Text, nullable=True)  # String de prueba para validar el regex
    priority = Column(Integer, default=0, nullable=False, index=True)  # Orden de aplicación (mayor = más prioridad)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    confidence_boost = Column(Float, default=0.0, nullable=False)  # Boost de confianza si match (+0.1, +0.2, etc)
    
    # GENERACIÓN CON AI (nuevos campos)
    generation_method = Column(String(50), default="manual", nullable=False)  # "manual", "ai_generated", "ai_refined"
    ai_model_used = Column(String(100), nullable=True)  # "gpt-4", "claude-3", etc. (solo si generation_method != "manual")
    ai_prompt_used = Column(Text, nullable=True)  # Prompt que se usó para generar la regla
    training_emails_count = Column(Integer, default=0, nullable=False)  # Cantidad de emails usados para entrenar
    training_emails_sample = Column(JSON, nullable=True)  # Muestra de emails usados (IDs o extractos)
    
    # Metadata
    description = Column(Text, nullable=True)  # Descripción humana del patrón
    example_input = Column(Text, nullable=True)  # Ejemplo de input que debe matchear
    example_output = Column(String(500), nullable=True)  # Ejemplo de output esperado
    created_by = Column(String(255), nullable=True)  # Usuario que creó la regla
    success_count = Column(Integer, default=0, nullable=False)  # Veces que ha sido exitosa
    failure_count = Column(Integer, default=0, nullable=False)  # Veces que ha fallado
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relaciones
    bank = relationship("Bank", back_populates="parsing_rules") 
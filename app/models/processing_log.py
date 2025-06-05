from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from app.core.database import Base

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String(50), nullable=False, index=True)  # import, parsing, transaction, health_check
    job_id = Column(Integer, nullable=True, index=True)  # ID del job relacionado (puede ser nulo para logs generales)
    level = Column(String(20), nullable=False, index=True)  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    message = Column(Text, nullable=False)  # Mensaje del log
    
    # Contexto adicional
    component = Column(String(100), nullable=True, index=True)  # EmailService, GmailClient, TransactionParser, etc
    operation = Column(String(100), nullable=True, index=True)  # get_emails, parse_transaction, create_user, etc
    user_id = Column(Integer, nullable=True, index=True)  # Usuario relacionado (si aplica)
    integration_id = Column(Integer, nullable=True, index=True)  # Integración relacionada (si aplica)
    email_id = Column(String(255), nullable=True, index=True)  # Email message_id relacionado (si aplica)
    
    # Metadata técnica
    execution_time_ms = Column(Integer, nullable=True)  # Tiempo de ejecución en milisegundos
    memory_usage_mb = Column(Integer, nullable=True)  # Uso de memoria en MB
    additional_data = Column(JSON, nullable=True)  # Datos adicionales en formato JSON
    
    # Stack trace para errores
    stack_trace = Column(Text, nullable=True)  # Stack trace completo para errores
    error_code = Column(String(50), nullable=True, index=True)  # Código de error personalizado
    
    # Request/Response data para APIs
    request_data = Column(JSON, nullable=True)  # Datos de request (para llamadas API)
    response_data = Column(JSON, nullable=True)  # Datos de response (para llamadas API)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, index=True)
    
    # Note: No hay relaciones FK para evitar dependency issues - usamos IDs como strings/integers 
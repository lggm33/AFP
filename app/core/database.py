import os
import hashlib
import json
import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

# Setup logging
logger = logging.getLogger(__name__)

# Base class para todos los modelos SQLAlchemy
Base = declarative_base()

# Global variables
engine = None
SessionLocal = None

def get_models_hash() -> str:
    """Generar hash de todos los archivos de modelos para detectar cambios"""
    models_dir = Path(__file__).parent.parent / "models"
    model_files = list(models_dir.glob("*.py"))
    
    # Concatenar contenido de todos los archivos de modelos
    combined_content = ""
    for file_path in sorted(model_files):
        if file_path.name != "__init__.py":
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    combined_content += f.read()
            except Exception as e:
                logger.warning(f"⚠️ No se pudo leer {file_path}: {e}")
    
    # Generar hash MD5
    return hashlib.md5(combined_content.encode('utf-8')).hexdigest()

def get_stored_models_hash() -> str:
    """Obtener hash guardado de la última vez"""
    hash_file = Path(__file__).parent.parent.parent / ".models_hash"
    try:
        if hash_file.exists():
            return hash_file.read_text().strip()
    except Exception as e:
        logger.warning(f"⚠️ Error leyendo hash guardado: {e}")
    return ""

def save_models_hash(hash_value: str):
    """Guardar hash actual de modelos"""
    hash_file = Path(__file__).parent.parent.parent / ".models_hash"
    try:
        hash_file.write_text(hash_value)
    except Exception as e:
        logger.warning(f"⚠️ Error guardando hash: {e}")

def should_recreate_tables() -> bool:
    """Determinar si las tablas deben recrearse por cambios en modelos"""
    # Solo en desarrollo
    env = os.getenv('ENVIRONMENT', 'development')
    if env == 'production':
        return False
    
    current_hash = get_models_hash()
    stored_hash = get_stored_models_hash()
    
    # Si es la primera vez o los hashes son diferentes
    if not stored_hash or current_hash != stored_hash:
        logger.info(f"🔄 Cambios detectados en modelos (hash: {current_hash[:8]}...)")
        return True
    
    return False

def get_database_url() -> str:
    """Obtener URL de base de datos desde env vars"""
    return os.environ.get(
        'DATABASE_URL', 
        'postgresql+psycopg://afp_user:afp_password@localhost:5432/afp_db'
    )

def init_database():
    """Inicializar base de datos automáticamente con detección de cambios"""
    global engine, SessionLocal
    
    logger.info("🔄 Inicializando base de datos...")
    
    try:
        # Crear engine
        DATABASE_URL = get_database_url()
        engine = create_engine(
            DATABASE_URL,
            echo=False,  # True para debug SQL
            pool_size=5,
            max_overflow=10
        )
        
        # Importar todos los modelos para que SQLAlchemy los conozca
        from app.models.user import User
        from app.models.integration import Integration
        from app.models.transaction import Transaction
        from app.models.email_import_job import EmailImportJob
        from app.models.email_parsing_job import EmailParsingJob
        from app.models.bank import Bank
        from app.models.transaction_parsing_job import TransactionParsingJob
        from app.models.parsing_rule import ParsingRule
        from app.models.processing_log import ProcessingLog
        from app.models.job_queue import JobQueue
        from app.models.bank_email_template import BankEmailTemplate
        
        # Detectar si necesitamos recrear tablas
        needs_recreate = should_recreate_tables()
        
        if needs_recreate:
            logger.info("🗑️ Eliminando tablas existentes...")
            Base.metadata.drop_all(bind=engine)
            logger.info("✨ Recreando tablas con nueva estructura...")
        
        # Crear/actualizar todas las tablas
        Base.metadata.create_all(bind=engine)
        
        # Guardar hash actual para próxima vez
        current_hash = get_models_hash()
        save_models_hash(current_hash)
        
        # Crear session factory
        SessionLocal = sessionmaker(bind=engine)
        
        status_msg = "recreadas" if needs_recreate else "verificadas"
        logger.info(f"✅ Base de datos inicializada correctamente (tablas {status_msg})")
        logger.info(f"📊 Tablas disponibles: {list(Base.metadata.tables.keys())}")
        
        return engine
        
    except Exception as e:
        logger.error(f"❌ Error inicializando base de datos: {str(e)}")
        raise

def get_db_session() -> Session:
    """Obtener nueva sesión de base de datos"""
    if SessionLocal is None:
        init_database()
    
    return SessionLocal()

def close_db_session(session: Session):
    """Cerrar sesión de base de datos"""
    try:
        session.close()
    except Exception as e:
        logger.warning(f"⚠️ Error cerrando sesión: {str(e)}")

# Context manager para sesiones
class DatabaseSession:
    def __init__(self):
        self.session = None
    
    def __enter__(self) -> Session:
        self.session = get_db_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type:
                self.session.rollback()
            else:
                self.session.commit()
            close_db_session(self.session)


# Thread-safe database session manager for workers
import threading

class ThreadSafeDB:
    """Thread-safe database object that creates sessions per thread"""
    
    def __init__(self):
        self._local = threading.local()
    
    @property
    def session(self):
        """Get session for current thread"""
        if not hasattr(self._local, 'session') or self._local.session is None:
            self._local.session = get_db_session()
        return self._local.session
    
    def commit(self):
        """Commit current thread's session"""
        if hasattr(self._local, 'session') and self._local.session:
            try:
                self._local.session.commit()
            except Exception as e:
                logger.error(f"Error committing session: {e}")
                self.rollback()
                raise
    
    def rollback(self):
        """Rollback current thread's session"""
        if hasattr(self._local, 'session') and self._local.session:
            try:
                self._local.session.rollback()
            except Exception as e:
                logger.error(f"Error rolling back session: {e}")
    
    def close(self):
        """Close current thread's session"""
        if hasattr(self._local, 'session') and self._local.session:
            try:
                close_db_session(self._local.session)
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            finally:
                self._local.session = None
    
    def refresh_session(self):
        """Force create a new session for current thread"""
        self.close()
        self._local.session = get_db_session()
        return self._local.session

# Global thread-safe db object for workers
db = ThreadSafeDB() 
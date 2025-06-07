#!/usr/bin/env python3
"""
Script para probar la nueva estructura de AFP
"""

import sys
import logging
from datetime import datetime, UTC

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Probar que todos los imports funcionan"""
    print("🧪 Probando imports de la nueva estructura...")
    
    try:
        # Core
        from app.core.database import init_database, get_db_session
        from app.core.exceptions import ValidationError, NotFoundError
        logger.info("✅ Core imports OK")
        
        # Models
        from app.models.user import User
        from app.models.transaction import Transaction
        from app.models.integration import Integration
        from app.models.email_import_job import EmailImportJob
        from app.models.email_parsing_job import EmailParsingJob
        from app.models.bank import Bank
        logger.info("✅ Models imports OK")
        
        # Infrastructure
        from app.infrastructure.email.gmail_client import GmailAPIClient
        logger.info("✅ Gmail client import OK")
        
        # Jobs
        from app.jobs.email_scheduler import EmailScheduler
        logger.info("✅ Jobs imports OK")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        return False

def test_database():
    """Probar conexión y creación de tablas"""
    print("\n🗄️  Probando base de datos...")
    
    try:
        from app.core.database import init_database
        
        # Inicializar BD
        engine = init_database()
        logger.info("✅ Base de datos inicializada")
        
        # Verificar tablas
        from app.infrastructure.database.db import Base
        tables = list(Base.metadata.tables.keys())
        logger.info(f"✅ Tablas creadas: {len(tables)}")
        for table in tables:
            logger.info(f"   • {table}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return False

def test_gmail_client():
    """Probar Gmail client (sin credenciales reales)"""
    print("\n📧 Probando Gmail client...")
    
    try:
        from app.infrastructure.email.gmail_client import GmailAPIClient
        
        # Crear cliente
        client = GmailAPIClient()
        logger.info("✅ Gmail client creado")
        
        # Verificar bancos configurados
        logger.info(f"✅ Bancos configurados: {len(client.bank_senders)}")
        for bank in client.bank_senders[:3]:  # Solo primeros 3
            logger.info(f"   • {bank}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Gmail client error: {e}")
        return False

def test_scheduler():
    """Probar scheduler (sin iniciarlo)"""
    print("\n⏰ Probando email scheduler...")
    
    try:
        from app.jobs.email_scheduler import EmailScheduler
        
        # Crear scheduler
        scheduler = EmailScheduler()
        logger.info("✅ Email scheduler creado")
        
        # Verificar status inicial
        status = scheduler.get_job_status()
        logger.info(f"✅ Scheduler status: running={status['running']}, jobs={status['jobs_count']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Scheduler error: {e}")
        return False

def test_models_creation():
    """Probar creación de modelos en BD"""
    print("\n🏗️  Probando creación de modelos...")
    
    try:
        from app.core.database import DatabaseSession
        from app.models.user import User
        from app.models.integration import Integration
        
        with DatabaseSession() as session:
            # Crear usuario de prueba
            test_user = User(
                email="test@afp.com",
                full_name="Usuario Test",
                created_at=datetime.now()
            )
            session.add(test_user)
            session.commit()
            
            logger.info(f"✅ Usuario creado con ID: {test_user.id}")
            
            # Crear integración de prueba
            test_integration = Integration(
                user_id=test_user.id,
                email_account="test@gmail.com",
                provider="gmail",
                created_at=datetime.now()
            )
            session.add(test_integration)
            session.commit()
            
            logger.info(f"✅ Integración creada con ID: {test_integration.id}")
            
            # Verificar relación
            user_integrations = session.query(Integration).filter_by(user_id=test_user.id).all()
            logger.info(f"✅ Usuario tiene {len(user_integrations)} integraciones")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Models error: {e}")
        return False

def main():
    """Ejecutar todas las pruebas"""
    print("🚀 AFP - Prueba de Nueva Estructura")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Database", test_database),
        ("Gmail Client", test_gmail_client),
        ("Scheduler", test_scheduler),
        ("Models Creation", test_models_creation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ Error en test {test_name}: {e}")
            results.append((test_name, False))
    
    # Resumen
    print("\n📊 Resumen de pruebas:")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Resultado: {passed}/{len(tests)} pruebas pasaron")
    
    if passed == len(tests):
        print("🎉 ¡Estructura nueva funcionando perfectamente!")
        print("🚀 Ya puedes ejecutar: ./start.sh")
        return 0
    else:
        print("⚠️  Hay problemas que necesitan resolución")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
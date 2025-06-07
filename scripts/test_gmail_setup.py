#!/usr/bin/env python3
"""
Script para probar la configuración de Gmail API y crear datos de prueba
"""

import sys
sys.path.insert(0, '.')

import logging
from datetime import datetime, UTC
from app.core.database import init_database, DatabaseSession
from app.models.user import User
from app.models.integration import Integration
from app.services.email_service import EmailService
from app.infrastructure.email.gmail_client import GmailAPIClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_database_connection():
    """Test 1: Verificar conexión a base de datos"""
    print("🔍 Test 1: Conexión a base de datos")
    try:
        init_database()
        print("✅ Base de datos conectada correctamente")
        return True
    except Exception as e:
        print(f"❌ Error en base de datos: {e}")
        return False

def test_gmail_client():
    """Test 2: Verificar Gmail API client"""
    print("\n🔍 Test 2: Gmail API Client")
    try:
        gmail_client = GmailAPIClient()
        print("✅ Gmail client creado")
        
        # Verificar archivos de credenciales
        import os
        if os.path.exists('credentials.json'):
            print("✅ credentials.json encontrado")
        else:
            print("❌ credentials.json NO encontrado")
            print("📋 Para configurar Gmail API:")
            print("   1. Ve a https://console.cloud.google.com/")
            print("   2. Habilita Gmail API")
            print("   3. Crea credenciales 'Desktop Application'")
            print("   4. Descarga como 'credentials.json'")
            return False
        
        # Intentar autenticación (abrirá navegador si es primera vez)
        print("🔐 Intentando autenticación...")
        if gmail_client.authenticate():
            print("✅ Autenticación Gmail exitosa")
            return True
        else:
            print("❌ Fallo en autenticación Gmail")
            return False
            
    except Exception as e:
        print(f"❌ Error en Gmail client: {e}")
        return False

def create_test_data():
    """Test 3: Crear datos de prueba"""
    print("\n🔍 Test 3: Crear datos de prueba")
    try:
        # Generar timestamp para email único
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_email = f"test_{timestamp}@example.com"
        
        with DatabaseSession() as session:
            # Crear usuario de prueba con timestamp
            test_user = User(
                email=test_email,
                full_name=f"Usuario de Prueba {timestamp}",
                is_active=True,
                created_at=datetime.now()
            )
            session.add(test_user)
            session.flush()  # Para obtener el ID
            
            # Crear integración de prueba
            integration = Integration(
                user_id=test_user.id,
                provider="gmail",
                email_account=f"test_{timestamp}@gmail.com",
                is_active=True,
                sync_frequency_minutes=5,
                created_at=datetime.now()
            )
            session.add(integration)
            session.commit()
            
            print(f"✅ Usuario creado: ID {test_user.id} - Email: {test_email}")
            print(f"✅ Integración creada: ID {integration.id}")
            return True
            
    except Exception as e:
        print(f"❌ Error creando datos de prueba: {e}")
        return False

def test_email_service():
    """Test 4: Probar EmailService"""
    print("\n🔍 Test 4: EmailService")
    try:
        email_service = EmailService()
        
        # Test conexión Gmail
        if email_service.test_gmail_connection():
            print("✅ EmailService - conexión Gmail OK")
        else:
            print("⚠️ EmailService - problema con Gmail (normal si no hay credentials.json)")
        
        # Test procesamiento (con datos de prueba)
        print("🔄 Probando procesamiento de usuarios...")
        results = email_service.process_all_active_users()
        
        print(f"✅ EmailService - resultados:")
        print(f"   👥 Usuarios procesados: {results['users_processed']}")
        print(f"   📧 Emails encontrados: {results['emails_found']}")
        print(f"   ✅ Emails procesados: {results['emails_processed']}")
        print(f"   🏷️ Labels agregados: {results.get('labels_added', 0)}")
        print(f"   ❌ Errores: {results['errors']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en EmailService: {e}")
        return False

def test_gmail_emails():
    """Test 5: Obtener emails reales (solo si hay credenciales)"""
    print("\n🔍 Test 5: Obtener emails reales de Gmail")
    try:
        gmail_client = GmailAPIClient()
        
        if not gmail_client.authenticate():
            print("⚠️ No se pudo autenticar - saltando test de emails reales")
            return True
        
        print("📧 Obteniendo emails bancarios...")
        emails = gmail_client.get_bank_emails(max_results=5)
        
        print(f"✅ Emails obtenidos: {len(emails)}")
        for i, email in enumerate(emails[:3], 1):  # Solo mostrar primeros 3
            print(f"   {i}. {email.get('subject', 'Sin asunto')[:50]}...")
            print(f"      From: {email.get('from', 'Desconocido')}")
            print(f"      Date: {email.get('date', 'Sin fecha')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error obteniendo emails: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("🚀 Testing Gmail API Setup para AFP")
    print("=" * 50)
    
    tests = [
        ("Base de datos", test_database_connection),
        ("Gmail Client", test_gmail_client),
        ("Datos de prueba", create_test_data),
        ("Email Service", test_email_service),
        ("Emails reales", test_gmail_emails)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error en test {name}: {e}")
            results.append((name, False))
    
    # Resumen final
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE TESTS:")
    
    passed = 0
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Tests pasados: {passed}/{len(results)}")
    
    if passed == len(results):
        print("🎉 ¡Todos los tests pasaron! Gmail API está listo.")
    else:
        print("⚠️ Algunos tests fallaron. Revisa la configuración.")

if __name__ == "__main__":
    main() 
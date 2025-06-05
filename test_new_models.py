#!/usr/bin/env python3
"""
Script para verificar que los nuevos modelos funcionan correctamente
"""

import sys
sys.path.insert(0, '.')

def main():
    print('🧪 VERIFICANDO NUEVOS MODELOS...')
    print('=' * 50)

    try:
        # Probar imports específicos
        from app.models import (
            User, Transaction, Integration, EmailImportJob, 
            EmailParsingJob, Bank, TransactionParsingJob, 
            ParsingRule, ProcessingLog
        )
        print('✅ Todos los imports funcionan')
        
        # Verificar que los nuevos modelos existen
        new_models = [
            ('TransactionParsingJob', TransactionParsingJob),
            ('ParsingRule', ParsingRule), 
            ('ProcessingLog', ProcessingLog)
        ]
        
        for model_name, model_class in new_models:
            if model_class:
                print(f'✅ {model_name} importado correctamente')
            else:
                print(f'❌ {model_name} NO encontrado')
        
        # Probar inicialización de base de datos
        from app.core.database import init_database
        engine = init_database()
        print('✅ Base de datos inicializada con nuevos modelos')
        
        # Mostrar tablas creadas
        from app.core.database import Base
        tables = list(Base.metadata.tables.keys())
        print(f'\n📊 TABLAS CREADAS ({len(tables)}):')
        for table in sorted(tables):
            print(f'   • {table}')
        
        # Verificar nuevas tablas específicamente
        expected_new_tables = [
            'transaction_parsing_jobs',
            'parsing_rules',
            'processing_logs'
        ]
        
        print(f'\n🔍 VERIFICANDO NUEVAS TABLAS:')
        for table in expected_new_tables:
            if table in tables:
                print(f'✅ {table}')
            else:
                print(f'❌ {table} NO CREADA')
                
        # Verificar relaciones en Bank
        print(f'\n🔗 VERIFICANDO RELACIONES MEJORADAS:')
        bank_columns = [col.name for col in Bank.__table__.columns]
        expected_bank_fields = ['sender_domains', 'sender_emails', 'keywords', 'parsing_priority']
        
        for field in expected_bank_fields:
            if field in bank_columns:
                print(f'✅ Bank.{field}')
            else:
                print(f'❌ Bank.{field} NO ENCONTRADO')
                
        print('\n🎉 VERIFICACIÓN COMPLETADA')
        
    except Exception as e:
        print(f'❌ ERROR: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
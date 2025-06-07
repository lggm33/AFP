#!/usr/bin/env python3
"""
Script para verificar todas las relaciones entre modelos
"""

import sys
sys.path.insert(0, '.')

def main():
    print('🔗 VERIFICANDO RELACIONES ENTRE MODELOS')
    print('=' * 60)

    try:
        from app.models import (
            User, Transaction, Integration, EmailImportJob, 
            EmailParsingJob, Bank, TransactionParsingJob, 
            ParsingRule, ProcessingLog
        )
        
        # Verificar relaciones de cada modelo
        print('\n👤 USER RELATIONSHIPS:')
        user_rels = [rel.key for rel in User.__mapper__.relationships]
        for rel in user_rels:
            print(f'   • User → {rel}')
        
        print('\n🏦 BANK RELATIONSHIPS:')
        bank_rels = [rel.key for rel in Bank.__mapper__.relationships]
        for rel in bank_rels:
            print(f'   • Bank → {rel}')
            
        print('\n🔗 INTEGRATION RELATIONSHIPS:')
        integration_rels = [rel.key for rel in Integration.__mapper__.relationships]
        for rel in integration_rels:
            print(f'   • Integration → {rel}')
            
        print('\n📥 EMAIL_IMPORT_JOB RELATIONSHIPS:')
        import_rels = [rel.key for rel in EmailImportJob.__mapper__.relationships]
        for rel in import_rels:
            print(f'   • EmailImportJob → {rel}')
            
        print('\n📧 EMAIL_PARSING_JOB RELATIONSHIPS:')
        parsing_rels = [rel.key for rel in EmailParsingJob.__mapper__.relationships]
        for rel in parsing_rels:
            print(f'   • EmailParsingJob → {rel}')
            
        print('\n💰 TRANSACTION RELATIONSHIPS:')
        transaction_rels = [rel.key for rel in Transaction.__mapper__.relationships]
        for rel in transaction_rels:
            print(f'   • Transaction → {rel}')
            
        print('\n📝 PARSING_RULE RELATIONSHIPS:')
        rule_rels = [rel.key for rel in ParsingRule.__mapper__.relationships]
        for rel in rule_rels:
            print(f'   • ParsingRule → {rel}')
            
        print('\n⚙️ TRANSACTION_PARSING_JOB RELATIONSHIPS:')
        tx_parsing_rels = [rel.key for rel in TransactionParsingJob.__mapper__.relationships]
        if tx_parsing_rels:
            for rel in tx_parsing_rels:
                print(f'   • TransactionParsingJob → {rel}')
        else:
            print('   • Sin relaciones (job independiente)')
            
        print('\n📊 PROCESSING_LOG RELATIONSHIPS:')
        log_rels = [rel.key for rel in ProcessingLog.__mapper__.relationships]
        if log_rels:
            for rel in log_rels:
                print(f'   • ProcessingLog → {rel}')
        else:
            print('   • Sin relaciones FK (evita dependency issues)')
        
        # Verificar Foreign Keys
        print('\n🔑 FOREIGN KEYS VERIFICATION:')
        
        models_with_fks = [
            ('Integration', Integration),
            ('EmailImportJob', EmailImportJob),
            ('EmailParsingJob', EmailParsingJob),
            ('Transaction', Transaction),
            ('ParsingRule', ParsingRule)
        ]
        
        for model_name, model_class in models_with_fks:
            fks = [col for col in model_class.__table__.columns if col.foreign_keys]
            if fks:
                print(f'   • {model_name}:')
                for fk_col in fks:
                    fk_target = list(fk_col.foreign_keys)[0].target_fullname
                    print(f'     - {fk_col.name} → {fk_target}')
            else:
                print(f'   • {model_name}: Sin FK')
        
        # Resumen de arquitectura
        print('\n🏗️ ARQUITECTURA RESULTANTE:')
        print('''
        User (1) ──────┬─→ Integration (N)
                       │   │
                       │   └─→ EmailImportJob (N)
                       │       │
                       │       └─→ EmailParsingJob (N) ──┬─→ Transaction (N)
                       │                                  │
                       │                                  └─→ Bank (1)
                       │                                      │
                       │                                      └─→ ParsingRule (N)
                       │
                       └─→ TransactionParsingJob (N) [independiente]
                       
        ProcessingLog [sin FK - solo IDs para audit]
        ''')
        
        print('✅ VERIFICACIÓN DE RELACIONES COMPLETADA')
        
    except Exception as e:
        print(f'❌ ERROR: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 
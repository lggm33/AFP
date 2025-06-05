#!/usr/bin/env python3
"""
Script para verificar si se están guardando los bodies de los emails
"""

import sys
sys.path.insert(0, '.')

from app.core.database import DatabaseSession
from app.models.email_parsing_job import EmailParsingJob

def main():
    with DatabaseSession() as session:
        # Obtener algunos emails para verificar si tienen body
        emails = session.query(EmailParsingJob).limit(5).all()
        
        print('🔍 VERIFICANDO SI SE GUARDA EL BODY DE LOS EMAILS:')
        print('=' * 70)
        
        emails_with_body = 0
        emails_without_body = 0
        
        for i, email in enumerate(emails, 1):
            print(f'\n📧 EMAIL {i}:')
            print(f'   Subject: {email.email_subject[:70]}...')
            print(f'   From: {email.email_from}')
            
            has_body = bool(email.email_body and email.email_body.strip())
            print(f'   Body guardado: {"SÍ" if has_body else "NO"}')
            
            if has_body:
                emails_with_body += 1
                # Mostrar primeros 200 caracteres del body
                body_preview = email.email_body[:200].replace('\n', ' ').replace('\r', '')
                print(f'   Body preview: {body_preview}...')
                print(f'   Body length: {len(email.email_body)} caracteres')
            else:
                emails_without_body += 1
                print(f'   Body preview: [VACÍO]')
            print('-' * 60)
        
        print(f'\n📊 RESUMEN:')
        print(f'   ✅ Emails CON body: {emails_with_body}')
        print(f'   ❌ Emails SIN body: {emails_without_body}')
        print(f'   📧 Total emails verificados: {len(emails)}')
        
        if emails_with_body == 0:
            print('\n⚠️ PROBLEMA: Ningún email tiene body guardado!')
        elif emails_without_body == 0:
            print('\n✅ PERFECTO: Todos los emails tienen body guardado!')
        else:
            print('\n⚠️ PARCIAL: Algunos emails tienen body, otros no.')

if __name__ == "__main__":
    main() 
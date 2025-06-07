#!/usr/bin/env python3
"""
Script para verificar qué emails están guardados en la base de datos
"""

import sys
sys.path.insert(0, '.')

from app.core.database import DatabaseSession
from app.models.email_parsing_job import EmailParsingJob
from app.models.email_import_job import EmailImportJob
from app.models.integration import Integration
from app.models.user import User

def main():
    with DatabaseSession() as session:
        # Contar registros
        users = session.query(User).count()
        integrations = session.query(Integration).count()
        import_jobs = session.query(EmailImportJob).count()
        parsing_jobs = session.query(EmailParsingJob).count()
        
        print('📊 DATOS EN LA BASE DE DATOS:')
        print(f'   👥 Usuarios: {users}')
        print(f'   🔗 Integraciones: {integrations}')
        print(f'   📥 Import Jobs: {import_jobs}')
        print(f'   📧 Emails guardados (Parsing Jobs): {parsing_jobs}')
        
        # Mostrar últimos 5 emails
        last_emails = session.query(EmailParsingJob).order_by(EmailParsingJob.created_at.desc()).limit(5).all()
        print(f'\n📧 ÚLTIMOS 5 EMAILS GUARDADOS:')
        for i, email in enumerate(last_emails, 1):
            print(f'   {i}. {email.email_subject[:60]}...')
            print(f'      From: {email.email_from[:50]}')
            print(f'      Message ID: {email.email_message_id}')
            print(f'      Status: {email.parsing_status}')
            print(f'      Created: {email.created_at}')
            print()
        
        # Mostrar import jobs
        import_jobs_data = session.query(EmailImportJob).order_by(EmailImportJob.created_at.desc()).limit(5).all()
        print(f'📥 ÚLTIMOS 5 IMPORT JOBS:')
        for i, job in enumerate(import_jobs_data, 1):
            print(f'   {i}. Status: {job.status}')
            print(f'      Emails encontrados: {job.emails_found}')
            print(f'      Emails procesados: {job.emails_processed}')
            print(f'      Started: {job.started_at}')
            print(f'      Completed: {job.completed_at}')
            print()
        
        # Verificar jobs en estado "running" (posibles huérfanos)
        running_jobs = session.query(EmailImportJob).filter(
            EmailImportJob.status == 'running',
            EmailImportJob.completed_at.is_(None)
        ).all()
        
        if running_jobs:
            print(f'⚠️ JOBS HUÉRFANOS (running sin completed_at): {len(running_jobs)}')
            for job in running_jobs:
                print(f'   ID: {job.id} - Started: {job.started_at}')
                print(f'   Integration: {job.integration_id}')
                print()
        else:
            print('✅ No hay jobs huérfanos')

if __name__ == "__main__":
    main() 
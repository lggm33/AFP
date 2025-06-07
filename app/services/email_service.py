import logging
from datetime import datetime, timedelta, UTC
from typing import List, Dict, Optional
from app.infrastructure.email.gmail_client import GmailAPIClient
from app.core.database import DatabaseSession
from app.models.integration import Integration
from app.models.email_import_job import EmailImportJob
from app.models.email_parsing_job import EmailParsingJob
from app.models.user import User

class EmailService:
    """Service para procesar emails de Gmail de todos los usuarios activos"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_all_active_users(self) -> Dict[str, int]:
        """Procesar emails para todos los usuarios con integraciones activas"""
        results = {
            'users_processed': 0,
            'emails_found': 0,
            'emails_processed': 0,
            'labels_added': 0,
            'errors': 0
        }
        
        try:
            with DatabaseSession() as session:
                # Obtener todas las integraciones activas
                active_integrations = session.query(Integration).filter(
                    Integration.is_active == True
                ).all()
                
                self.logger.info(f"📧 Procesando {len(active_integrations)} integraciones activas")
                
                for integration in active_integrations:
                    try:
                        user_result = self._process_user_emails(integration)
                        results['users_processed'] += 1
                        results['emails_found'] += user_result['emails_found']
                        results['emails_processed'] += user_result['emails_processed']
                        results['labels_added'] += user_result.get('labels_added', 0)
                        
                    except Exception as e:
                        results['errors'] += 1
                        self.logger.error(f"❌ Error procesando usuario {integration.user_id}: {str(e)}")
                
                self.logger.info(f"✅ Procesamiento completado: {results}")
                return results
                
        except Exception as e:
            self.logger.error(f"❌ Error en procesamiento masivo: {str(e)}")
            results['errors'] += 1
            return results
    
    def _process_user_emails(self, integration: Integration) -> Dict[str, int]:
        """Process emails for a specific user"""
        result = {'emails_found': 0, 'emails_processed': 0, 'labels_added': 0}
        
        try:
            # Create import job and get its ID
            with DatabaseSession() as session:
                import_job = EmailImportJob(
                    integration_id=integration.id,
                    status='running',
                    started_at=datetime.now()
                )
                session.add(import_job)
                session.commit()
                import_job_id = import_job.id  # Save ID for later use
            
            # Create Gmail client
            gmail_client = GmailAPIClient()
            
            # Determine if this is the first run for this integration
            is_first_run = self._is_first_run(integration)
            
            # Determine date from which to search (client now handles this intelligently)
            since_date = self._get_last_sync_date(integration) if not is_first_run else None
            
            # Get bank emails with optimized logic
            emails = gmail_client.get_bank_emails(
                since_date=since_date, 
                max_results=50,
                is_first_run=is_first_run
            )
            result['emails_found'] = len(emails)
            
            # Process each email
            for email_data in emails:
                try:
                    # Save email to database
                    self._process_single_email(email_data, import_job_id)
                    result['emails_processed'] += 1
                    
                    # Add AFP_Processed label to email in Gmail
                    if gmail_client.add_afp_label_to_email(email_data['gmail_id']):
                        result['labels_added'] += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ Error processing email {email_data.get('message_id', 'unknown')}: {str(e)}")
            
            # Update job as completed
            with DatabaseSession() as session:
                job = session.get(EmailImportJob, import_job_id)
                job.status = 'completed'
                job.emails_found = result['emails_found']
                job.emails_processed = result['emails_processed']
                job.completed_at = datetime.now()
                session.commit()
            
            self.logger.info(f"✅ User {integration.user_id}: {result['emails_processed']}/{result['emails_found']} emails processed, {result['labels_added']} labels added")
            return result
            
        except Exception as e:
            # Mark job as failed
            with DatabaseSession() as session:
                job = session.get(EmailImportJob, import_job_id)
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.now()
                session.commit()
            raise
    
    def _is_first_run(self, integration: Integration) -> bool:
        """Check if this is the first run for this integration by looking at import jobs"""
        try:
            with DatabaseSession() as session:
                last_job = session.query(EmailImportJob).filter(
                    EmailImportJob.integration_id == integration.id,
                    EmailImportJob.status == 'completed'
                ).order_by(EmailImportJob.completed_at.desc()).first()
                
                return last_job is None
        except Exception:
            return True  # Assume first run if there's an error
    
    def _get_last_sync_date(self, integration: Integration) -> datetime:
        """Get last sync date from completed import jobs or default date"""
        try:
            with DatabaseSession() as session:
                last_job = session.query(EmailImportJob).filter(
                    EmailImportJob.integration_id == integration.id,
                    EmailImportJob.status == 'completed'
                ).order_by(EmailImportJob.completed_at.desc()).first()
                
                if last_job and last_job.completed_at:
                    return last_job.completed_at
                else:
                    # First sync: last 7 days
                    return datetime.now() - timedelta(days=7)
        except Exception:
            # Default: last 7 days
            return datetime.now() - timedelta(days=7)
    
    def _process_single_email(self, email_data: Dict, import_job_id: int):
        """Procesar un email individual"""
        try:
            with DatabaseSession() as session:
                # Verificar si ya existe este email
                existing = session.query(EmailParsingJob).filter(
                    EmailParsingJob.email_message_id == email_data['message_id']
                ).first()
                
                if existing:
                    self.logger.debug(f"📧 Email {email_data['message_id']} ya existe, saltando")
                    return
                
                # Crear registro de parsing job
                parsing_job = EmailParsingJob(
                    email_import_job_id=import_job_id,
                    email_message_id=email_data['message_id'],
                    email_subject=email_data.get('subject', '')[:500],
                    email_from=email_data.get('from', '')[:255],
                    email_body=email_data.get('body', ''),
                    status='waiting',
                    created_at=datetime.now()
                )
                
                session.add(parsing_job)
                session.commit()
                
                self.logger.debug(f"📧 Email guardado para parsing: {email_data['subject'][:50]}...")
                
        except Exception as e:
            self.logger.error(f"❌ Error guardando email: {str(e)}")
            raise
    
    def test_gmail_connection(self) -> bool:
        """Probar conexión con Gmail API"""
        try:
            gmail_client = GmailAPIClient()
            return gmail_client.test_connection()
        except Exception as e:
            self.logger.error(f"❌ Error probando Gmail: {str(e)}")
            return False
    
    def setup_user_integration(self, user_id: int, email_account: str) -> bool:
        """Configurar integración Gmail para un usuario (placeholder por ahora)"""
        try:
            with DatabaseSession() as session:
                # Verificar si ya existe integración para este usuario
                existing = session.query(Integration).filter(
                    Integration.user_id == user_id,
                    Integration.email_account == email_account
                ).first()
                
                if existing:
                    self.logger.info(f"✅ Integración ya existe para usuario {user_id}")
                    return True
                
                # Crear nueva integración
                integration = Integration(
                    user_id=user_id,
                    provider='gmail',
                    email_account=email_account,
                    is_active=True,
                    sync_frequency_minutes=5,
                    created_at=datetime.now()
                )
                
                session.add(integration)
                session.commit()
                
                self.logger.info(f"✅ Integración Gmail creada para usuario {user_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Error configurando integración: {str(e)}")
            return False 
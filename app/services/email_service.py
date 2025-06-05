import logging
from datetime import datetime, timedelta
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
        """Procesar emails para un usuario específico"""
        result = {'emails_found': 0, 'emails_processed': 0, 'labels_added': 0}
        
        try:
            # Crear job de importación y obtener su ID
            with DatabaseSession() as session:
                import_job = EmailImportJob(
                    integration_id=integration.id,
                    status='running',
                    started_at=datetime.now()
                )
                session.add(import_job)
                session.commit()
                import_job_id = import_job.id  # Guardar ID para usar después
            
            # Crear cliente Gmail
            gmail_client = GmailAPIClient()
            
            # Determinar si es primer run para esta integración
            is_first_run = integration.last_sync is None
            
            # Determinar fecha desde cuándo buscar (el cliente ahora maneja esto inteligentemente)
            since_date = self._get_last_sync_date(integration) if not is_first_run else None
            
            # Obtener emails bancarios con lógica optimizada
            emails = gmail_client.get_bank_emails(
                since_date=since_date, 
                max_results=50,
                is_first_run=is_first_run
            )
            result['emails_found'] = len(emails)
            
            # Procesar cada email
            for email_data in emails:
                try:
                    # Guardar email en base de datos
                    self._process_single_email(email_data, import_job_id)
                    result['emails_processed'] += 1
                    
                    # Agregar label AFP_Processed al email en Gmail
                    if gmail_client.add_afp_label_to_email(email_data['gmail_id']):
                        result['labels_added'] += 1
                    
                except Exception as e:
                    self.logger.error(f"❌ Error procesando email {email_data.get('message_id', 'unknown')}: {str(e)}")
            
            # Actualizar job como completado
            with DatabaseSession() as session:
                job = session.get(EmailImportJob, import_job_id)
                job.status = 'completed'
                job.emails_found = result['emails_found']
                job.emails_processed = result['emails_processed']
                job.completed_at = datetime.now()
                session.commit()
            
            # Actualizar última sincronización
            with DatabaseSession() as session:
                integ = session.get(Integration, integration.id)
                integ.last_sync = datetime.now()
                session.commit()
            
            self.logger.info(f"✅ Usuario {integration.user_id}: {result['emails_processed']}/{result['emails_found']} emails procesados, {result['labels_added']} labels agregados")
            return result
            
        except Exception as e:
            # Marcar job como fallido
            with DatabaseSession() as session:
                job = session.get(EmailImportJob, import_job_id)
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = datetime.now()
                session.commit()
            raise
    
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
                    parsing_status='pending',
                    created_at=datetime.now()
                )
                
                session.add(parsing_job)
                session.commit()
                
                self.logger.debug(f"📧 Email guardado para parsing: {email_data['subject'][:50]}...")
                
        except Exception as e:
            self.logger.error(f"❌ Error guardando email: {str(e)}")
            raise
    
    def _get_last_sync_date(self, integration: Integration) -> datetime:
        """Obtener fecha de última sincronización o fecha por defecto"""
        if integration.last_sync:
            return integration.last_sync
        else:
            # Primera sincronización: últimos 7 días
            return datetime.now() - timedelta(days=7)
    
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
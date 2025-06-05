import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from app.services.email_service import EmailService

class EmailScheduler:
    """Scheduler para procesamiento automático de emails bancarios"""
    
    def __init__(self):
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Configurar scheduler
        jobstore = MemoryJobStore()
        self.scheduler = BackgroundScheduler(
            jobstores={'default': jobstore},
            job_defaults={
                'coalesce': True,  # Evitar jobs duplicados
                'max_instances': 1,  # Un job a la vez
                'misfire_grace_time': 300  # 5 min grace period
            }
        )
        
        # Email service
        self.email_service = EmailService()
        
    def start(self):
        """Iniciar el scheduler"""
        try:
            # Job principal: procesar emails cada 5 minutos
            self.scheduler.add_job(
                func=self.process_emails_job,
                trigger='interval',
                minutes=5,
                id='process_emails',
                name='Process Bank Emails',
                replace_existing=True,
                next_run_time=datetime.now()  # Ejecutar inmediatamente al inicio
            )
            
            # Job de test: verificar conexión cada hora
            self.scheduler.add_job(
                func=self.test_connection_job,
                trigger='interval',
                hours=1,
                id='test_connection',
                name='Test Gmail Connection',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.logger.info("✅ Email scheduler iniciado - Jobs cada 5 minutos")
            
        except Exception as e:
            self.logger.error(f"❌ Error iniciando scheduler: {str(e)}")
            raise
    
    def process_emails_job(self):
        """Job principal de procesamiento de emails usando EmailService"""
        try:
            self.logger.info("🔄 Iniciando procesamiento automático de emails...")
            
            # Usar EmailService para procesar todos los usuarios
            results = self.email_service.process_all_active_users()
            
            # Resumen final
            self.logger.info(f"✅ Procesamiento automático completado:")
            self.logger.info(f"   👥 Usuarios procesados: {results['users_processed']}")
            self.logger.info(f"   📧 Emails encontrados: {results['emails_found']}")
            self.logger.info(f"   ✅ Emails procesados: {results['emails_processed']}")
            self.logger.info(f"   🏷️ Labels agregados: {results['labels_added']}")
            self.logger.info(f"   ❌ Errores: {results['errors']}")
            
            if results['errors'] > 0:
                self.logger.warning(f"⚠️ Se encontraron {results['errors']} errores durante el procesamiento")
                
        except Exception as e:
            self.logger.error(f"❌ Error inesperado en procesamiento automático: {str(e)}")
    
    def test_connection_job(self):
        """Job para probar conexión con Gmail API"""
        try:
            self.logger.info("🔍 Probando conexión Gmail API...")
            
            if self.email_service.test_gmail_connection():
                self.logger.info("✅ Conexión Gmail API OK")
            else:
                self.logger.warning("⚠️ Problema con conexión Gmail API")
                
        except Exception as e:
            self.logger.error(f"❌ Error probando conexión: {str(e)}")
    
    def stop(self):
        """Detener el scheduler"""
        try:
            self.scheduler.shutdown(wait=True)
            self.logger.info("📅 Email scheduler detenido")
        except Exception as e:
            self.logger.error(f"❌ Error deteniendo scheduler: {str(e)}")
    
    def get_job_status(self):
        """Obtener estado actual de los jobs"""
        jobs = self.scheduler.get_jobs()
        return {
            'running': self.scheduler.running,
            'jobs_count': len(jobs),
            'jobs': [
                {
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in jobs
            ]
        }

# Instancia global del scheduler
email_scheduler = EmailScheduler()

# Funciones de conveniencia para compatibilidad
def start_scheduler():
    """Función de compatibilidad"""
    email_scheduler.start()

def stop_scheduler():
    """Función de compatibilidad"""
    email_scheduler.stop() 
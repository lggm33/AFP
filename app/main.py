import logging
import atexit
from flask import Flask, jsonify
from app.core.database import init_database
from app.jobs.email_scheduler import email_scheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('afp.log')
    ]
)

logger = logging.getLogger(__name__)

def create_app():
    """Crear y configurar la aplicación Flask"""
    app = Flask(__name__)
    
    # Health check endpoint
    @app.route('/health')
    def health():
        scheduler_status = email_scheduler.get_job_status()
        return jsonify({
            'status': 'ok',
            'message': 'AFP funcionando correctamente',
            'database': 'connected',
            'scheduler': {
                'running': scheduler_status['running'],
                'jobs_count': scheduler_status['jobs_count'],
                'next_email_check': scheduler_status['jobs'][0]['next_run_time'] if scheduler_status['jobs'] else None
            }
        })
    
    # Endpoint para forzar procesamiento manual
    @app.route('/api/process-emails', methods=['POST'])
    def process_emails_manual():
        try:
            email_scheduler.process_emails_job()
            return jsonify({
                'status': 'success',
                'message': 'Procesamiento de emails ejecutado manualmente'
            })
        except Exception as e:
            logger.error(f"Error en procesamiento manual: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # Endpoint para ver status del scheduler
    @app.route('/api/scheduler/status')
    def scheduler_status():
        return jsonify(email_scheduler.get_job_status())
    
    return app

def main():
    """Función principal - inicializar todo y ejecutar"""
    try:
        logger.info("🚀 Iniciando AFP (Aplicación de Finanzas Personales)...")
        
        # 1. Inicializar base de datos
        logger.info("📊 Inicializando base de datos...")
        init_database()
        
        # 2. Crear aplicación Flask
        logger.info("🌐 Creando aplicación Flask...")
        app = create_app()
        
        # 3. Iniciar email scheduler
        logger.info("📅 Iniciando email scheduler...")
        email_scheduler.start()
        
        # 4. Configurar cleanup al salir
        atexit.register(email_scheduler.stop)
        
        # 5. Mostrar información de inicio
        logger.info("✅ AFP iniciado exitosamente!")
        logger.info("📍 Endpoints disponibles:")
        logger.info("   • http://localhost:8000/health - Health check")
        logger.info("   • http://localhost:8000/api/process-emails - Procesar emails manualmente")
        logger.info("   • http://localhost:8000/api/scheduler/status - Estado del scheduler")
        logger.info("📧 Procesamiento automático cada 5 minutos")
        
        # 6. Iniciar servidor Flask
        app.run(
            host='0.0.0.0',
            port=8000,
            debug=False,  # False para evitar doble scheduler
            use_reloader=False
        )
        
    except Exception as e:
        logger.error(f"❌ Error fatal iniciando AFP: {str(e)}")
        raise

if __name__ == "__main__":
    main()
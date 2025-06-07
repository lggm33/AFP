import logging
import atexit
import threading
from flask import Flask, jsonify
from app.core.database import init_database
from app.workers.worker_manager import WorkerManager

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

def create_app(worker_manager):
    """Crear y configurar la aplicación Flask"""
    app = Flask(__name__)
    
    # Health check endpoint
    @app.route('/health')
    def health():
        system_status = worker_manager.get_system_status()
        return jsonify({
            'status': 'ok',
            'message': 'AFP funcionando correctamente',
            'database': 'connected',
            'workers': {
                'manager_running': system_status['manager_running'],
                'total_workers': system_status['total_workers'],
                'alive_workers': system_status['alive_workers'],
                'healthy_workers': system_status['healthy_workers']
            }
        })
    
    # Endpoint para ver status completo del sistema
    @app.route('/api/workers/status')
    def workers_status():
        return jsonify(worker_manager.get_system_status())
    
    # Endpoint para ver workers individuales
    @app.route('/api/workers')
    def workers_list():
        status = worker_manager.get_system_status()
        return jsonify({
            'workers': status['workers'],
            'summary': {
                'total': status['total_workers'],
                'alive': status['alive_workers'],
                'healthy': status['healthy_workers']
            }
        })
    
    return app

def main():
    """Función principal - inicializar todo y ejecutar"""
    worker_manager = None
    
    try:
        logger.info("🚀 Iniciando AFP (Aplicación de Finanzas Personales)...")
        
        # 1. Inicializar base de datos
        logger.info("📊 Inicializando base de datos...")
        init_database()
        
        # 2. Ejecutar setup inicial (crear usuario y integración)
        logger.info("🔧 Ejecutando setup inicial...")
        from app.setup.initial_setup import run_initial_setup
        run_initial_setup()
        
        # 3. Inicializar WorkerManager
        logger.info("🔧 Inicializando Worker Manager...")
        worker_manager = WorkerManager()
        
        # 4. Crear aplicación Flask
        logger.info("🌐 Creando aplicación Flask...")
        app = create_app(worker_manager)
        
        # 5. Configurar cleanup al salir
        atexit.register(lambda: worker_manager.stop_all_workers() if worker_manager else None)
        
        # 6. Iniciar workers en thread separado
        logger.info("⚙️ Iniciando workers...")
        worker_thread = threading.Thread(
            target=worker_manager.start_all_workers,
            daemon=True
        )
        worker_thread.start()
        
        # 7. Mostrar información de inicio
        logger.info("✅ AFP iniciado exitosamente!")
        logger.info("📍 Endpoints disponibles:")
        logger.info("   • http://localhost:8000/health - Health check")
        logger.info("   • http://localhost:8000/api/workers - Lista de workers")
        logger.info("   • http://localhost:8000/api/workers/status - Estado completo")
        logger.info("🔧 Workers funcionando:")
        logger.info("   • JobDetector: Detecta integraciones cada 30s")
        logger.info("   • EmailImport: Importa emails continuamente")
        logger.info("   • ParsingDetector: Detecta emails para parsing cada 15s")
        logger.info("   • TransactionCreation: Crea transacciones continuamente")
        
        # 8. Iniciar servidor Flask
        app.run(
            host='0.0.0.0',
            port=8000,
            debug=False,  # False para evitar conflictos con workers
            use_reloader=False
        )
        
    except KeyboardInterrupt:
        logger.info("👋 Recibida señal de interrupción")
    except Exception as e:
        logger.error(f"❌ Error fatal iniciando AFP: {str(e)}")
        raise
    finally:
        if worker_manager:
            logger.info("🛑 Deteniendo workers...")
            worker_manager.stop_all_workers()

if __name__ == "__main__":
    main()
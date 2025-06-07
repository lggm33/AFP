import logging
import time
import signal
import sys
from datetime import datetime, UTC
from typing import List, Dict, Any

from .job_detector_worker import JobDetectorWorker
from .email_import_worker import EmailImportWorker
from .parsing_detector_worker import ParsingDetectorWorker
from .transaction_creation_worker import TransactionCreationWorker


class WorkerManager:
    """
    Manager that coordinates and monitors all workers.
    
    Responsibilities:
    - Start and stop all workers
    - Monitor worker health
    - Restart failed workers
    - Handle graceful shutdown
    - Provide system status
    """
    
    def __init__(self):
        self.workers = []
        self.is_running = False
        self.logger = logging.getLogger("WorkerManager")
        self.logger.setLevel(logging.INFO)
        
        # Setup logging if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - WorkerManager - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start_all_workers(self):
        """Start all workers"""
        if self.is_running:
            self.logger.warning("Workers are already running")
            return
        
        self.logger.info("Starting all workers...")
        
        try:
            # Initialize workers
            workers_to_start = [
                JobDetectorWorker(),
                EmailImportWorker(),
                ParsingDetectorWorker(), 
                TransactionCreationWorker()
            ]
            
            # Start each worker
            for worker in workers_to_start:
                try:
                    worker.start()
                    self.workers.append(worker)
                    self.logger.info(f"Started worker: {worker.name}")
                except Exception as e:
                    self.logger.error(f"Failed to start worker {worker.name}: {str(e)}")
            
            self.is_running = True
            self.logger.info(f"Successfully started {len(self.workers)} workers")
            
            # Start monitoring loop
            self.monitor_workers()
            
        except Exception as e:
            self.logger.error(f"Error starting workers: {str(e)}")
            self.stop_all_workers()
            raise
    
    def stop_all_workers(self):
        """Stop all workers gracefully"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping all workers...")
        self.is_running = False
        
        # Signal all workers to stop
        for worker in self.workers:
            try:
                worker.stop()
                self.logger.info(f"Signaled worker {worker.name} to stop")
            except Exception as e:
                self.logger.error(f"Error stopping worker {worker.name}: {str(e)}")
        
        # Wait for workers to stop
        for worker in self.workers:
            try:
                worker.join(timeout=10)  # Wait up to 10 seconds for each worker
                if worker.is_alive():
                    self.logger.warning(f"Worker {worker.name} did not stop gracefully")
                else:
                    self.logger.info(f"Worker {worker.name} stopped")
            except Exception as e:
                self.logger.error(f"Error waiting for worker {worker.name}: {str(e)}")
        
        self.workers.clear()
        self.logger.info("All workers stopped")
    
    def monitor_workers(self):
        """Monitor worker health and restart if needed"""
        self.logger.info("Starting worker monitoring...")
        
        try:
            while self.is_running:
                time.sleep(30)  # Check every 30 seconds
                
                if not self.is_running:
                    break
                
                # Check health of each worker
                for i, worker in enumerate(self.workers[:]):  # Create copy to avoid modification during iteration
                    try:
                        if not worker.is_alive():
                            self.logger.warning(f"Worker {worker.name} is dead, restarting...")
                            self._restart_worker(i)
                        elif not worker.is_healthy():
                            self.logger.warning(f"Worker {worker.name} is unhealthy, restarting...")
                            self._restart_worker(i)
                    except Exception as e:
                        self.logger.error(f"Error checking worker {worker.name}: {str(e)}")
                
                # Log status
                self.logger.info(f"Worker status: {self._get_worker_summary()}")
                
        except KeyboardInterrupt:
            self.logger.info("Monitoring interrupted")
        except Exception as e:
            self.logger.error(f"Error in worker monitoring: {str(e)}")
        finally:
            self.logger.info("Worker monitoring stopped")
    
    def _restart_worker(self, worker_index: int):
        """Restart a specific worker"""
        if worker_index >= len(self.workers):
            return
        
        old_worker = self.workers[worker_index]
        worker_name = old_worker.name
        
        try:
            # Stop old worker
            old_worker.stop()
            if old_worker.is_alive():
                old_worker.join(timeout=5)
            
            # Create new worker of the same type
            new_worker = self._create_worker_by_name(worker_name)
            if new_worker:
                new_worker.start()
                self.workers[worker_index] = new_worker
                self.logger.info(f"Successfully restarted worker: {worker_name}")
            else:
                self.logger.error(f"Failed to create new worker: {worker_name}")
                
        except Exception as e:
            self.logger.error(f"Error restarting worker {worker_name}: {str(e)}")
    
    def _create_worker_by_name(self, name: str):
        """Create a new worker instance by name"""
        worker_classes = {
            'JobDetector': JobDetectorWorker,
            'EmailImport': EmailImportWorker,
            'ParsingDetector': ParsingDetectorWorker,
            'TransactionCreation': TransactionCreationWorker
        }
        
        worker_class = worker_classes.get(name)
        if worker_class:
            return worker_class()
        return None
    
    def _get_worker_summary(self) -> str:
        """Get a summary of worker status"""
        alive_count = sum(1 for w in self.workers if w.is_alive())
        healthy_count = sum(1 for w in self.workers if w.is_alive() and w.is_healthy())
        
        return f"{healthy_count}/{alive_count} healthy, {alive_count}/{len(self.workers)} alive"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get detailed system status"""
        workers_status = []
        
        for worker in self.workers:
            status = worker.get_status()
            status['is_alive'] = worker.is_alive()
            workers_status.append(status)
        
        return {
            'manager_running': self.is_running,
            'total_workers': len(self.workers),
            'alive_workers': sum(1 for w in self.workers if w.is_alive()),
            'healthy_workers': sum(1 for w in self.workers if w.is_alive() and w.is_healthy()),
            'workers': workers_status,
            'timestamp': datetime.now(UTC).isoformat()
        }
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop_all_workers()
        sys.exit(0)
    
    def run_forever(self):
        """Run the worker manager indefinitely"""
        try:
            self.start_all_workers()
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Error running worker manager: {str(e)}")
        finally:
            self.stop_all_workers()


# Entry point for running as a script
if __name__ == "__main__":
    manager = WorkerManager()
    manager.run_forever() 
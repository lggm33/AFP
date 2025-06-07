import threading
import time
import logging
import uuid
from datetime import datetime, UTC
from abc import ABC, abstractmethod
from typing import Optional

from ..core.database import db


class BaseWorker(ABC, threading.Thread):
    """
    Base class for all workers with common functionality:
    - Threading support
    - Database connection management
    - Logging
    - Error handling
    - Graceful shutdown
    - Heartbeat monitoring
    """
    
    def __init__(self, name: str, sleep_interval: float = 1.0):
        super().__init__(daemon=True)
        self.name = name
        self.worker_id = str(uuid.uuid4())
        self.sleep_interval = sleep_interval
        self.is_running = False
        self.should_stop = False
        self.last_heartbeat = None
        self.error_count = 0
        self.max_errors = 10
        
        # Setup logging
        self.logger = logging.getLogger(f"Worker.{name}")
        self.logger.setLevel(logging.INFO)
        
        # Create handler if not exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                f'%(asctime)s - {self.name}[{self.worker_id[:8]}] - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def run(self):
        """Main thread execution loop"""
        self.logger.info(f"Starting worker {self.name}")
        self.is_running = True
        
        try:
            while not self.should_stop:
                try:
                    self.update_heartbeat()
                    self.process_cycle()
                    self.error_count = 0  # Reset error count on successful cycle
                    
                except Exception as e:
                    self.error_count += 1
                    error_str = str(e)
                    self.logger.error(f"Error in worker cycle: {error_str}")
                    
                    # Handle specific database connection errors
                    if "concurrent operations are not permitted" in error_str or "This transaction is closed" in error_str:
                        self.logger.warning("Database connection conflict detected - refreshing session")
                        try:
                            db.refresh_session()
                            self.logger.info("Database session refreshed successfully")
                        except Exception as refresh_error:
                            self.logger.error(f"Error refreshing session: {refresh_error}")
                    else:
                        # For other errors, try regular rollback
                        try:
                            if hasattr(db.session, 'is_active') and db.session.is_active:
                                db.session.rollback()
                                self.logger.debug("Database transaction rolled back")
                        except Exception as rollback_error:
                            # Log but don't fail - rollback conflicts are common in concurrent systems
                            self.logger.debug(f"Rollback conflict (expected): {str(rollback_error)}")
                    
                    if self.error_count >= self.max_errors:
                        self.logger.critical(f"Max errors ({self.max_errors}) reached. Stopping worker.")
                        break
                
                # Sleep before next cycle
                time.sleep(self.sleep_interval)
                
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        finally:
            self.cleanup()
            self.is_running = False
            self.logger.info(f"Worker {self.name} stopped")
    
    @abstractmethod
    def process_cycle(self):
        """
        Process one cycle of work. Must be implemented by subclasses.
        This method should contain the main logic of the worker.
        """
        pass
    
    def update_heartbeat(self):
        """Update heartbeat timestamp"""
        self.last_heartbeat = datetime.now(UTC)
    
    def stop(self):
        """Signal worker to stop gracefully"""
        self.logger.info(f"Stopping worker {self.name}")
        self.should_stop = True
    
    def is_healthy(self) -> bool:
        """Check if worker is healthy based on heartbeat"""
        if not self.last_heartbeat:
            return False
        
        # Consider unhealthy if no heartbeat in last 60 seconds
        time_since_heartbeat = (datetime.now(UTC) - self.last_heartbeat).total_seconds()
        return time_since_heartbeat < 60
    
    def cleanup(self):
        """Cleanup resources before stopping"""
        try:
            # Refresh session to ensure clean state
            db.refresh_session()
            
            # Reset any running jobs assigned to this worker
            self.reset_worker_jobs()
            db.session.commit()
            self.logger.info("Worker cleanup completed successfully")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            try:
                db.rollback()
            except Exception as rollback_error:
                self.logger.debug(f"Cleanup rollback conflict (expected): {str(rollback_error)}")
        finally:
            # Always close the session on cleanup
            try:
                db.close()
            except Exception as close_error:
                self.logger.debug(f"Session close conflict (expected): {str(close_error)}")
    
    def reset_worker_jobs(self):
        """Reset jobs that were being processed by this worker"""
        # This will be overridden by workers that need to reset specific jobs
        pass
    
    def get_status(self) -> dict:
        """Get worker status information"""
        return {
            'name': self.name,
            'worker_id': self.worker_id,
            'is_running': self.is_running,
            'is_healthy': self.is_healthy(),
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'error_count': self.error_count,
            'sleep_interval': self.sleep_interval
        } 
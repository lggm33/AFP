#!/usr/bin/env python3
"""
Simple test script for AFP workers with real database
"""

import sys
import time
from datetime import datetime, UTC

# Add current directory to path
sys.path.insert(0, '.')

def test_worker_imports():
    """Test that all workers can be imported"""
    print("📦 Testing worker imports...")
    
    try:
        from app.workers import (
            BaseWorker, 
            JobDetectorWorker, 
            EmailImportWorker, 
            ParsingDetectorWorker, 
            TransactionCreationWorker, 
            WorkerManager
        )
        print("   ✅ All workers imported successfully")
        return True
    except Exception as e:
        print(f"   ❌ Import failed: {str(e)}")
        return False

def test_base_worker():
    """Test BaseWorker functionality"""
    print("\n🔧 Testing BaseWorker...")
    
    from app.workers.base_worker import BaseWorker
    
    class TestWorker(BaseWorker):
        def __init__(self):
            super().__init__(name="TestWorker", sleep_interval=0.1)
            self.cycles_run = 0
            self.max_cycles = 2
        
        def process_cycle(self):
            self.cycles_run += 1
            print(f"   Cycle {self.cycles_run}/{self.max_cycles}")
            
            if self.cycles_run >= self.max_cycles:
                self.stop()
    
    # Test worker
    worker = TestWorker()
    print(f"   Worker ID: {worker.worker_id[:8]}...")
    print(f"   Worker name: {worker.name}")
    
    # Test quick execution
    print("   Starting worker for 2 cycles...")
    worker.start()
    worker.join(timeout=3)  # Wait max 3 seconds
    
    if worker.cycles_run == 2:
        print("   ✅ BaseWorker test passed")
        return True
    else:
        print(f"   ❌ BaseWorker test failed (ran {worker.cycles_run}/2 cycles)")
        return False

def test_worker_creation():
    """Test that all workers can be created"""
    print("\n🏗️ Testing worker creation...")
    
    from app.workers import (
        JobDetectorWorker, 
        EmailImportWorker, 
        ParsingDetectorWorker, 
        TransactionCreationWorker
    )
    
    workers = [
        ("JobDetector", JobDetectorWorker),
        ("EmailImport", EmailImportWorker),
        ("ParsingDetector", ParsingDetectorWorker),
        ("TransactionCreation", TransactionCreationWorker)
    ]
    
    created_workers = []
    
    for name, WorkerClass in workers:
        try:
            worker = WorkerClass()
            status = worker.get_status()
            print(f"   ✅ {name}: {worker.name} (interval: {worker.sleep_interval}s)")
            created_workers.append(worker)
        except Exception as e:
            print(f"   ❌ {name}: Failed to create - {str(e)}")
            return False
    
    print(f"   ✅ Successfully created {len(created_workers)} workers")
    return True

def test_worker_manager():
    """Test WorkerManager creation"""
    print("\n🎛️ Testing WorkerManager...")
    
    from app.workers.worker_manager import WorkerManager
    
    try:
        manager = WorkerManager()
        status = manager.get_system_status()
        
        print(f"   Manager running: {status['manager_running']}")
        print(f"   Total workers: {status['total_workers']}")
        print(f"   ✅ WorkerManager created successfully")
        return True
    except Exception as e:
        print(f"   ❌ WorkerManager creation failed: {str(e)}")
        return False

def test_database_connection():
    """Test database connection"""
    print("\n💾 Testing database connection...")
    
    try:
        from app.core.database import get_db_session, Base
        
        # Test session creation
        session = get_db_session()
        
        # Test query (should work even if tables are empty)
        from app.models.user import User
        users = session.query(User).limit(1).all()
        
        session.close()
        
        print(f"   ✅ Database connection successful")
        print(f"   Available tables: {list(Base.metadata.tables.keys())[:5]}...")
        return True
    except Exception as e:
        print(f"   ❌ Database connection failed: {str(e)}")
        return False

def main():
    """Run all basic tests"""
    print("🚀 AFP Workers Basic Test Suite")
    print("=" * 50)
    
    tests = [
        ("Imports", test_worker_imports),
        ("Database", test_database_connection),
        ("BaseWorker", test_base_worker),
        ("Worker Creation", test_worker_creation),
        ("WorkerManager", test_worker_manager)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"   ❌ {test_name} failed with exception: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All basic tests passed!")
        print("\n🔄 Workers are ready to run!")
        print("Next steps:")
        print("  1. Use './start.sh' to start the full system")
        print("  2. Or run individual workers for testing")
        return True
    else:
        print("⚠️ Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 
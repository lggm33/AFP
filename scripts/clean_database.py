#!/usr/bin/env python3
"""
Clean database completely - start fresh.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database, db, engine
from app.models.user import User
from app.models.integration import Integration
from app.models.email_import_job import EmailImportJob
from app.models.email_parsing_job import EmailParsingJob
from app.models.bank import Bank
from app.models.parsing_rule import ParsingRule
from app.models.transaction import Transaction
from app.models.job_queue import JobQueue
from app.models.processing_log import ProcessingLog

def clean_all_data():
    """Delete all data from all tables"""
    print("🧹 CLEANING ALL DATABASE DATA")
    print("="*50)
    
    try:
        # Delete in reverse dependency order
        print("Deleting ProcessingLog...")
        db.session.query(ProcessingLog).delete()
        
        print("Deleting JobQueue...")
        db.session.query(JobQueue).delete()
        
        print("Deleting Transaction...")
        db.session.query(Transaction).delete()
        
        print("Deleting ParsingRule...")
        db.session.query(ParsingRule).delete()
        
        print("Deleting EmailParsingJob...")
        db.session.query(EmailParsingJob).delete()
        
        print("Deleting Bank...")
        db.session.query(Bank).delete()
        
        print("Deleting EmailImportJob...")
        db.session.query(EmailImportJob).delete()
        
        print("Deleting Integration...")
        db.session.query(Integration).delete()
        
        print("Deleting User...")
        db.session.query(User).delete()
        
        # Commit all deletions
        db.session.commit()
        print("✅ All data deleted successfully")
        
    except Exception as e:
        print(f"❌ Error cleaning data: {str(e)}")
        db.session.rollback()
        raise

def reset_sequences():
    """Reset all auto-increment sequences"""
    print("\n🔄 RESETTING AUTO-INCREMENT SEQUENCES")
    print("="*50)
    
    try:
        tables = [
            'users', 'integrations', 'email_import_jobs', 
            'email_parsing_jobs', 'banks', 'parsing_rules', 
            'transactions', 'job_queue', 'processing_logs'
        ]
        
        for table in tables:
            try:
                db.session.execute(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1")
                print(f"✅ Reset sequence for {table}")
            except Exception as e:
                print(f"⚠️  Could not reset sequence for {table}: {str(e)}")
        
        db.session.commit()
        print("✅ Sequences reset successfully")
        
    except Exception as e:
        print(f"❌ Error resetting sequences: {str(e)}")
        db.session.rollback()

def verify_clean():
    """Verify database is completely clean"""
    print("\n✅ VERIFYING CLEAN DATABASE")
    print("="*50)
    
    try:
        models = [
            (User, 'users'),
            (Integration, 'integrations'),
            (EmailImportJob, 'email_import_jobs'),
            (EmailParsingJob, 'email_parsing_jobs'),
            (Bank, 'banks'),
            (ParsingRule, 'parsing_rules'),
            (Transaction, 'transactions'),
            (JobQueue, 'job_queue'),
            (ProcessingLog, 'processing_logs')
        ]
        
        all_clean = True
        for model, name in models:
            count = db.session.query(model).count()
            if count == 0:
                print(f"✅ {name}: 0 records")
            else:
                print(f"❌ {name}: {count} records remaining")
                all_clean = False
        
        if all_clean:
            print("\n🎉 DATABASE IS COMPLETELY CLEAN!")
        else:
            print("\n⚠️  Some data remains in database")
            
        return all_clean
        
    except Exception as e:
        print(f"❌ Error verifying clean database: {str(e)}")
        return False

def main():
    """Main function"""
    try:
        # Initialize database
        init_database()
        print("✅ Database connection established")
        
        # Clean all data
        clean_all_data()
        
        # Reset sequences
        reset_sequences()
        
        # Verify clean
        success = verify_clean()
        
        if success:
            print("\n🎯 READY FOR FRESH START!")
            print("Database is completely clean and ready for new data.")
            return 0
        else:
            print("\n❌ CLEANUP INCOMPLETE")
            return 1
            
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main()) 
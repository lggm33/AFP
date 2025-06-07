#!/usr/bin/env python3
"""
Test initial setup script
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_database
from app.setup.initial_setup import run_initial_setup

def main():
    print("🧪 TESTING INITIAL SETUP")
    print("="*50)
    
    try:
        # Initialize database
        init_database()
        print("✅ Database initialized")
        
        # Run initial setup
        result = run_initial_setup()
        
        print(f"\n✅ Setup completed successfully!")
        print(f"User ID: {result['user'].id}")
        print(f"Integration ID: {result['integration'].id}")
        print(f"EmailImportJob ID: {result['email_import_job'].id}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 
#!/usr/bin/env python3
"""
Complete database reset script for AFP
- Drops the entire database
- Recreates the database from scratch
- Creates all tables with new structure
- Optionally runs initial setup
"""
import sys
import os
import psycopg
from psycopg import sql
sys.path.insert(0, '.')

def get_db_config():
    """Extract database configuration from environment"""
    db_url = os.getenv('DATABASE_URL', 'postgresql+psycopg://afp_user:afp_password@localhost:5432/afp_db')
    # Parse the URL to extract components
    # postgresql+psycopg://afp_user:afp_password@localhost:5432/afp_db
    parts = db_url.replace('postgresql+psycopg://', '').split('@')
    user_pass = parts[0].split(':')
    host_port_db = parts[1].split('/')
    host_port = host_port_db[0].split(':')
    
    return {
        'user': user_pass[0],
        'password': user_pass[1],
        'host': host_port[0],
        'port': int(host_port[1]),
        'database': host_port_db[1]
    }

def drop_and_create_database():
    """Drop and recreate the entire database"""
    config = get_db_config()
    db_name = config['database']
    
    print(f"🗑️ Dropping database '{db_name}'...")
    
    try:
        # Connect to postgres database to drop/create our target database
        admin_conn_string = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/postgres"
        
        # Connect as admin to drop/create database
        with psycopg.connect(admin_conn_string) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                # Terminate existing connections to the database
                print("   🔌 Terminating existing connections...")
                cur.execute(sql.SQL("""
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s AND pid <> pg_backend_pid()
                """), [db_name])
                
                # Drop database
                print(f"   ⬇️ Dropping database '{db_name}'...")
                cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(db_name)
                ))
                
                # Create database
                print(f"   ⬆️ Creating database '{db_name}'...")
                cur.execute(sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(db_name)
                ))
                
        print("   ✅ Database dropped and recreated successfully")
        return True
        
    except Exception as e:
        print(f"   ❌ Error with database operations: {e}")
        return False

def create_tables():
    """Create all tables with new structure"""
    print("🏗️ Creating tables with new structure...")
    try:
        # Use the same initialization that the main app uses
        from app.core.database import init_database
        
        print("   🔄 Initializing database connection...")
        init_database()
        
        print("   ✅ Tables created successfully by init_database()")
        print("   📊 The init_database() function handles table creation automatically")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_optional_setup():
    """Optionally run initial setup"""
    print("\n🔧 OPTIONAL: Initial Setup")
    print("   This will create default user, integration, banks, and parsing rules")
    
    try:
        choice = input("   Do you want to run initial setup? (y/n): ").lower().strip()
        if choice in ['y', 'yes']:
            print("   🚀 Running initial setup...")
            from app.setup.initial_setup import run_initial_setup
            
            success = run_initial_setup()
            if success:
                print("   ✅ Initial setup completed successfully")
                
                # Show what was created
                from app.core.database import db
                from app.models.user import User
                from app.models.integration import Integration
                from app.models.bank import Bank
                from app.models.parsing_rule import ParsingRule
                
                with db.session:
                    user_count = db.session.query(User).count()
                    integration_count = db.session.query(Integration).count()
                    bank_count = db.session.query(Bank).count()
                    rule_count = db.session.query(ParsingRule).count()
                
                print(f"      👥 Users created: {user_count}")
                print(f"      🔗 Integrations created: {integration_count}")
                print(f"      🏦 Banks created: {bank_count}")
                print(f"      📋 Parsing rules created: {rule_count}")
            else:
                print("   ⚠️ Initial setup had issues")
        else:
            print("   ⏭️ Skipping initial setup")
            
    except KeyboardInterrupt:
        print("\n   ⏭️ Skipping initial setup")
    except Exception as e:
        print(f"   ❌ Error in initial setup: {e}")

def main():
    print("🔄 COMPLETE DATABASE RESET FOR AFP")
    print("="*60)
    print("⚠️  WARNING: This will COMPLETELY DELETE the database!")
    print("   • Entire database will be dropped")
    print("   • Database will be recreated from scratch")
    print("   • All data will be permanently lost")
    print("")
    
    # Confirmation prompt
    try:
        confirmation = input("Are you absolutely sure? Type 'DELETE' to confirm: ").strip()
        if confirmation != 'DELETE':
            print("❌ Operation cancelled - confirmation not matched")
            return False
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        return False
    
    print("\n🚀 Starting complete database reset...")
    
    try:
        # Step 1: Drop and recreate database
        print("\n1️⃣ Dropping and recreating database...")
        if not drop_and_create_database():
            return False
        
        # Step 2: Create all tables
        print("\n2️⃣ Creating tables...")
        if not create_tables():
            return False
        
        # Step 3: Optional setup
        run_optional_setup()
        
        print("\n" + "="*60)
        print("🎉 DATABASE RESET COMPLETED!")
        print("="*60)
        print("✅ Database has been completely reset:")
        print("   🆕 Fresh database with latest table structure")
        print("   📊 All models/tables created successfully")
        print("   🔧 Models hash updated")
        print("")
        print("🚀 You can now start the system with: ./start.sh")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR during reset: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Reset failed - check the errors above")
        sys.exit(1)
    else:
        print("\n✅ Reset completed successfully!")
        sys.exit(0) 
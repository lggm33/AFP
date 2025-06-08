#!/usr/bin/env python3
"""
Fix bank configuration with real email addresses and domains from actual emails
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import DatabaseSession
from app.models.bank import Bank

def fix_bank_configurations():
    print("🔧 FIXING BANK CONFIGURATIONS")
    print("=" * 60)
    
    with DatabaseSession() as db:
        # Fix BAC Costa Rica
        bac_bank = db.query(Bank).filter_by(bank_code='BAC').first()
        if bac_bank:
            print(f"📝 Updating BAC Costa Rica...")
            print(f"   Old emails: {bac_bank.sender_emails}")
            print(f"   Old domains: {bac_bank.sender_domains}")
            
            bac_bank.sender_emails = ['notificacion@notificacionesbaccr.com']
            bac_bank.sender_domains = ['notificacionesbaccr.com', 'baccredomatic.com']
            bac_bank.domain = 'notificacionesbaccr.com'
            
            print(f"   New emails: {bac_bank.sender_emails}")
            print(f"   New domains: {bac_bank.sender_domains}")
            print("   ✅ BAC Updated")
        
        # Fix Scotiabank Costa Rica
        scotia_bank = db.query(Bank).filter_by(bank_code='SCOTIA').first()
        if scotia_bank:
            print(f"\n📝 Updating Scotiabank Costa Rica...")
            print(f"   Old emails: {scotia_bank.sender_emails}")
            print(f"   Old domains: {scotia_bank.sender_domains}")
            
            scotia_bank.sender_emails = ['AlertasScotiabank@scotiabank.com']
            scotia_bank.sender_domains = ['scotiabank.com']
            scotia_bank.domain = 'scotiabank.com'
            
            print(f"   New emails: {scotia_bank.sender_emails}")
            print(f"   New domains: {scotia_bank.sender_domains}")
            print("   ✅ Scotiabank Updated")
        
        # Commit changes
        db.commit()
        print(f"\n💾 Changes committed to database")
        
        # Verify changes
        print(f"\n🔍 VERIFICATION:")
        print("-" * 40)
        banks = db.query(Bank).filter_by(is_active=True).all()
        for bank in banks:
            print(f"{bank.name}:")
            print(f"  emails: {bank.sender_emails}")
            print(f"  domains: {bank.sender_domains}")

if __name__ == "__main__":
    fix_bank_configurations() 
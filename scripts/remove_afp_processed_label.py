#!/usr/bin/env python3
"""
Script to remove AFP_Processed label from Gmail emails
Usage:
    python scripts/remove_afp_processed_label.py --all            # Remove from all emails
    python scripts/remove_afp_processed_label.py --count 10      # Remove from last 10 emails
    python scripts/remove_afp_processed_label.py --days 7       # Remove from emails of last 7 days
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.email.gmail_client import GmailAPIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AFPLabelRemover:
    """Class to handle removal of AFP_Processed labels"""
    
    def __init__(self):
        self.gmail_client = GmailAPIClient()
        self.AFP_LABEL_NAME = 'AFP_Processed'
        self.afp_label_id = None
        
    def authenticate(self) -> bool:
        """Authenticate with Gmail API"""
        try:
            if not self.gmail_client.authenticate():
                logger.error("❌ Failed to authenticate with Gmail API")
                return False
            
            # Get AFP label ID
            self.afp_label_id = self.gmail_client.afp_label_id
            if not self.afp_label_id:
                logger.warning("⚠️ AFP_Processed label not found - nothing to remove")
                return False
                
            logger.info(f"✅ Authentication successful, AFP label ID: {self.afp_label_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Authentication error: {str(e)}")
            return False
    
    def get_emails_with_afp_label(self, max_results: int = None, days_back: int = None) -> list:
        """Get emails that have the AFP_Processed label"""
        try:
            query_parts = [f'label:{self.AFP_LABEL_NAME}']
            
            # Add date filter if specified
            if days_back:
                date_limit = datetime.now() - timedelta(days=days_back)
                date_str = date_limit.strftime('%Y/%m/%d')
                query_parts.append(f'after:{date_str}')
            
            query = ' '.join(query_parts)
            logger.info(f"🔍 Searching for emails with query: {query}")
            
            # Search for messages
            results = self.gmail_client.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results if max_results else 500  # Default limit
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"📧 Found {len(messages)} emails with AFP_Processed label")
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ Error getting emails with AFP label: {str(e)}")
            return []
    
    def remove_afp_label_from_email(self, message_id: str) -> bool:
        """Remove AFP_Processed label from a single email"""
        try:
            self.gmail_client.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': [self.afp_label_id]}
            ).execute()
            
            logger.debug(f"✅ Removed AFP label from email: {message_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error removing label from email {message_id}: {str(e)}")
            return False
    
    def remove_labels_bulk(self, message_ids: list) -> dict:
        """Remove AFP_Processed label from multiple emails"""
        results = {
            'total': len(message_ids),
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        logger.info(f"🔄 Starting bulk removal of AFP labels from {len(message_ids)} emails...")
        
        for i, message_id in enumerate(message_ids, 1):
            try:
                if self.remove_afp_label_from_email(message_id):
                    results['success'] += 1
                else:
                    results['failed'] += 1
                
                # Progress indicator
                if i % 10 == 0 or i == len(message_ids):
                    logger.info(f"📊 Progress: {i}/{len(message_ids)} emails processed")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"Email {message_id}: {str(e)}")
                logger.error(f"❌ Failed to process email {message_id}: {str(e)}")
        
        return results
    
    def remove_all_afp_labels(self) -> dict:
        """Remove AFP_Processed label from ALL emails"""
        logger.warning("⚠️ REMOVING AFP LABELS FROM ALL EMAILS")
        
        # Get all emails with AFP label
        messages = self.get_emails_with_afp_label()
        if not messages:
            logger.info("✅ No emails found with AFP_Processed label")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        # Extract message IDs
        message_ids = [msg['id'] for msg in messages]
        
        # Remove labels
        return self.remove_labels_bulk(message_ids)
    
    def remove_afp_labels_by_count(self, count: int) -> dict:
        """Remove AFP_Processed label from last N emails"""
        logger.info(f"🎯 Removing AFP labels from last {count} emails")
        
        # Get emails with limit
        messages = self.get_emails_with_afp_label(max_results=count)
        if not messages:
            logger.info("✅ No emails found with AFP_Processed label")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        # Extract message IDs
        message_ids = [msg['id'] for msg in messages]
        
        # Remove labels
        return self.remove_labels_bulk(message_ids)
    
    def remove_afp_labels_by_days(self, days: int) -> dict:
        """Remove AFP_Processed label from emails of last N days"""
        logger.info(f"📅 Removing AFP labels from emails of last {days} days")
        
        # Get emails from last N days
        messages = self.get_emails_with_afp_label(days_back=days)
        if not messages:
            logger.info("✅ No emails found with AFP_Processed label in the specified period")
            return {'total': 0, 'success': 0, 'failed': 0}
        
        # Extract message IDs
        message_ids = [msg['id'] for msg in messages]
        
        # Remove labels
        return self.remove_labels_bulk(message_ids)

def main():
    """Main script execution"""
    parser = argparse.ArgumentParser(
        description='Remove AFP_Processed labels from Gmail emails',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/remove_afp_processed_label.py --all        # Remove from all emails
  python scripts/remove_afp_processed_label.py --count 10   # Remove from last 10 emails
  python scripts/remove_afp_processed_label.py --days 7     # Remove from last 7 days
        """
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true', help='Remove label from ALL emails')
    group.add_argument('--count', type=int, help='Remove label from last N emails')
    group.add_argument('--days', type=int, help='Remove label from emails of last N days')
    
    parser.add_argument('--confirm', action='store_true', 
                       help='Skip confirmation prompt (use with caution)')
    
    args = parser.parse_args()
    
    # Initialize remover
    remover = AFPLabelRemover()
    
    # Authenticate
    if not remover.authenticate():
        logger.error("❌ Cannot proceed without authentication")
        return 1
    
    # Confirm action (unless --confirm flag is used)
    if not args.confirm:
        if args.all:
            action_desc = "ALL emails with AFP_Processed label"
        elif args.count:
            action_desc = f"last {args.count} emails with AFP_Processed label"
        elif args.days:
            action_desc = f"emails with AFP_Processed label from last {args.days} days"
        
        print(f"\n⚠️  You are about to remove AFP_Processed labels from: {action_desc}")
        print("   This action cannot be undone!")
        
        confirmation = input("\nDo you want to continue? (yes/no): ").lower().strip()
        if confirmation not in ['yes', 'y']:
            print("❌ Operation cancelled by user")
            return 0
    
    # Execute removal
    try:
        logger.info("🚀 Starting AFP label removal operation...")
        
        if args.all:
            results = remover.remove_all_afp_labels()
        elif args.count:
            results = remover.remove_afp_labels_by_count(args.count)
        elif args.days:
            results = remover.remove_afp_labels_by_days(args.days)
        
        # Show results
        logger.info("📊 OPERATION COMPLETED")
        logger.info(f"   Total emails processed: {results['total']}")
        logger.info(f"   ✅ Successfully removed: {results['success']}")
        logger.info(f"   ❌ Failed: {results['failed']}")
        
        if results.get('errors'):
            logger.warning("\n⚠️ Errors encountered:")
            for error in results['errors'][:5]:  # Show first 5 errors
                logger.warning(f"   • {error}")
            if len(results['errors']) > 5:
                logger.warning(f"   ... and {len(results['errors']) - 5} more errors")
        
        if results['success'] > 0:
            logger.info(f"\n🎉 Successfully removed AFP_Processed labels from {results['success']} emails!")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
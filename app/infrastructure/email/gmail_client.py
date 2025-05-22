import imapclient, email
from app.config import settings

def get_recent_emails(limit=10):
    with imapclient.IMAPClient(settings.IMAP_SERVER) as client:
        client.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
        client.select_folder('INBOX', readonly=True)
        messages = client.search(['UNSEEN'])
        for uid, message_data in client.fetch(messages[-limit:], ['RFC822']).items():
            msg = email.message_from_bytes(message_data[b'RFC822'])
            yield {
                "subject": msg["subject"],
                "from": msg["from"],
                "body": msg.get_payload(decode=True),
                "message_id": msg["Message-ID"]
            }

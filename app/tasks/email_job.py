from apscheduler.schedulers.background import BackgroundScheduler
from app.infrastructure.email import get_recent_emails

def process_emails():
    for msg in get_recent_emails():
        # TODO: Parsear, extraer monto, fecha y guardar en DB
        print(f"Procesando correo: {msg['subject']}")

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(process_emails, 'interval', minutes=5)
    scheduler.start()

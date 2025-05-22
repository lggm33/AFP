from flask import Flask
from app.tasks.email_job import start_scheduler
from app.infrastructure.database.db import Base, engine
from app.domain.models import Transaction

app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    app.run(debug=True)
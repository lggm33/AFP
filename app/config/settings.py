import os
from dotenv import load_dotenv

def reload_env():
    dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    load_dotenv(dotenv_path, override=True)

# Initial load
reload_env()

def get_env_var(key):
    reload_env()  # Reload env variables before getting them
    return os.getenv(key)

DATABASE_URL = get_env_var("DATABASE_URL")
EMAIL_ADDRESS = get_env_var("EMAIL_ADDRESS")
EMAIL_PASSWORD = get_env_var("EMAIL_PASSWORD")
IMAP_SERVER = get_env_var("IMAP_SERVER")

import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME")
TOKEN_ENCRYPTION_KEY = os.getenv("SHA256_KEY")
EMAIL = os.getenv("EMAIL")
USER_TYPE=os.getenv("USER_TYPE")
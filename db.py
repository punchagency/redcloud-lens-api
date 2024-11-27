import os

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

DB_USERNAME = os.environ.get("DB_USERNAME", None)
DB_PASSWORD = os.environ.get("DB_PASSWORD", None)
DB_HOST = os.environ.get("DB_HOST", None)
DB_NAME = os.environ.get("DB_NAME", None)

# Configure database connection
DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func

# Database URL (SQLite in this case)
DATABASE_URL = "sqlite:///./conversations.db"

# Create engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

# Base for models
Base = declarative_base()


# Conversation model
class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, index=True)
    chat_id = Column(String)
    user_content = Column(Text, nullable=False)  
    ai_content = Column(Text, nullable=False)  
    created_at = Column(DateTime, server_default=func.now())


# Initialize the database
def initialize_database():
    Base.metadata.create_all(bind=engine)

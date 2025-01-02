import uuid
from typing import List, Optional

from db.store import Conversation, SessionLocal


# Create a new conversation
def create_conversation(user_content: str, ai_content: str) -> Conversation:
    session = SessionLocal()
    try:
        conversation_id = str(uuid.uuid4())
        chat_id = str(uuid.uuid4())
        conversation = Conversation(
            id=conversation_id,
            chat_id=chat_id,
            user_content=user_content,
            ai_content=ai_content,
        )
        session.add(conversation)
        session.commit()
        return conversation
    finally:
        session.close()


# Retrieve conversation history
def get_conversation(chat_id: str) -> Optional[List[Conversation]]:
    session = SessionLocal()
    try:
        conversation = (
            session.query(Conversation)
            .filter(Conversation.chat_id == chat_id)
            .order_by(Conversation.created_at.desc())
            .limit(10)
        )
        if conversation:
            return conversation
        return None
    finally:
        session.close()


# Save a message to the conversation
def save_message(chat_id: str, user_content: str, ai_content: str):
    session = SessionLocal()
    try:
        conversation = (
            session.query(Conversation).filter(Conversation.chat_id == chat_id).first()
        )
        if conversation:
            conversation.user_content = user_content  # Append new user content
            conversation.ai_content = ai_content
            session.commit()
    finally:
        session.close()

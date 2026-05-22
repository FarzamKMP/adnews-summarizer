"""
Jonas-style RAG chat service.
Retrieves relevant persona notes → builds prompt → calls Gemini.
"""
import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from modules.ai import gemini_client
from modules.ai.prompt_templates import JONAS_SYSTEM_PROMPT
from modules.rag import vector_store
from modules.storage.models import Conversation, Message

logger = logging.getLogger(__name__)

# Jonas baseline persona (seed context — always injected)
JONAS_BASE_PROFILE = """
Jonas Bailly is Managing Director of Jung von Matt HAVEL, Partner at Jung von Matt Group,
Founder of Jung von Matt START, and Board Member of GWA.
Inferred professional traits (from public sources):
- Strategic, brand-oriented, commercially grounded
- Strong passion for creativity and communication
- Collaborative, high-energy, persistent leadership style
- Values agency identity, team culture, and client impact
- Interest in startups, innovation, and new agency models
Communication style:
- Direct but warm; strategic before tactical
- Confident without arrogance
- Practical framing: "What is the real opportunity?", "What is the client tension?"
- Focused on people, client value, and culturally relevant ideas
""".strip()

MAX_HISTORY_MESSAGES = 10


def get_or_create_conversation(db: Session, conversation_id: str | None) -> Conversation:
    if conversation_id:
        conv = db.query(Conversation).filter_by(id=conversation_id).first()
        if conv:
            conv.updated_at = datetime.utcnow()
            db.commit()
            return conv
    conv = Conversation(id=str(uuid.uuid4()))
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def _load_history(db: Session, conversation_id: str) -> list[Message]:
    return (
        db.query(Message)
        .filter_by(conversation_id=conversation_id)
        .order_by(Message.created_at.asc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )


def _format_history(messages: list[Message]) -> str:
    if not messages:
        return "No prior conversation."
    return "\n".join(f"{m.role.upper()}: {m.content}" for m in messages)


def _retrieve_rag_context(query: str, n: int = 4) -> str:
    if vector_store.count() == 0:
        return "No knowledge base entries yet."
    try:
        results = vector_store.query(query, n_results=n)
        if not results:
            return "No relevant notes found."
        return "\n\n---\n\n".join(r["text"] for r in results)
    except Exception as e:
        logger.warning(f"RAG retrieval failed: {e}")
        return "Knowledge base unavailable."


def chat(db: Session, message: str, conversation_id: str | None = None) -> dict:
    """
    Process one user message and return assistant reply + conversation_id.
    """
    conv = get_or_create_conversation(db, conversation_id)

    # Save user message
    user_msg = Message(conversation_id=conv.id, role="user", content=message)
    db.add(user_msg)
    db.commit()

    history = _load_history(db, conv.id)
    rag_context = _retrieve_rag_context(message)
    history_text = _format_history(history[:-1])  # exclude message just saved

    prompt = JONAS_SYSTEM_PROMPT.format(
        persona_context=JONAS_BASE_PROFILE,
        rag_context=rag_context,
        history=history_text,
    ) + f"\n\nUSER: {message}\n\nASSISTANT:"

    try:
        reply = gemini_client.generate(prompt)
    except Exception as e:
        logger.error(f"Gemini chat failed: {e}")
        reply = "I'm sorry, I encountered an error processing your request. Please check the Gemini API configuration."

    assistant_msg = Message(conversation_id=conv.id, role="assistant", content=reply)
    db.add(assistant_msg)
    db.commit()

    return {
        "conversation_id": conv.id,
        "reply": reply,
        "rag_context_used": rag_context != "No knowledge base entries yet."
            and rag_context != "No relevant notes found.",
    }

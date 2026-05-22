"""
CRUD for PersonaNote + automatic RAG indexing.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from modules.rag import vector_store
from modules.storage.models import PersonaNote

logger = logging.getLogger(__name__)


def list_notes(db: Session, tag: Optional[str] = None) -> list[PersonaNote]:
    q = db.query(PersonaNote)
    if tag:
        q = q.filter(PersonaNote.tags.contains(tag))
    return q.order_by(PersonaNote.created_at.desc()).all()


def get_note(db: Session, note_id: str) -> Optional[PersonaNote]:
    return db.query(PersonaNote).filter_by(id=note_id).first()


def create_note(
    db: Session,
    title: str,
    content: str,
    tags: list[str] | None = None,
    is_seed: bool = False,
) -> PersonaNote:
    note = PersonaNote(
        title=title,
        content=content,
        tags=",".join(tags or []),
        is_seed=is_seed,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    _index_note(note)
    return note


def update_note(
    db: Session,
    note_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> Optional[PersonaNote]:
    note = get_note(db, note_id)
    if not note:
        return None
    if title is not None:
        note.title = title
    if content is not None:
        note.content = content
    if tags is not None:
        note.tags = ",".join(tags)
    note.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    _index_note(note)
    return note


def delete_note(db: Session, note_id: str) -> bool:
    note = get_note(db, note_id)
    if not note:
        return False
    db.delete(note)
    db.commit()
    try:
        vector_store.delete_document(f"note:{note_id}")
    except Exception as e:
        logger.warning(f"Vector delete failed for note {note_id}: {e}")
    return True


def reindex_all(db: Session) -> int:
    notes = db.query(PersonaNote).all()
    count = 0
    for note in notes:
        try:
            _index_note(note)
            count += 1
        except Exception as e:
            logger.warning(f"Reindex failed for note {note.id}: {e}")
    logger.info(f"Reindexed {count} notes")
    return count


def _index_note(note: PersonaNote) -> None:
    text = f"{note.title}\n{note.content}"
    vector_store.upsert_document(
        doc_id=f"note:{note.id}",
        text=text,
        metadata={"type": "persona_note", "tags": note.tags, "title": note.title},
    )

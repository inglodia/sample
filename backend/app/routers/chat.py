import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.chat import ChatMessage, ChatThread
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreateIn,
    ChatMessageListOut,
    ChatMessageOut,
    ChatThreadCreateIn,
    ChatThreadListOut,
    ChatThreadOut,
    ChatTurnOut,
)
from app.services.chat import HistoryMessage, run_turn

router = APIRouter()


def _get_owned_thread(
    db: Session, thread_id: uuid.UUID, user: User
) -> ChatThread:
    thread = db.get(ChatThread, thread_id)
    if thread is None or thread.user_id != user.id:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


def _title_from_content(content: str) -> str:
    cleaned = " ".join(content.strip().split())
    if not cleaned:
        return "New chat"
    return cleaned[:80]


@router.get("/threads", response_model=ChatThreadListOut)
def list_threads(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatThreadListOut:
    threads = db.scalars(
        select(ChatThread)
        .where(ChatThread.user_id == user.id)
        .order_by(ChatThread.updated_at.desc())
    ).all()
    return ChatThreadListOut(items=[ChatThreadOut.model_validate(t) for t in threads])


@router.post("/threads", response_model=ChatThreadOut, status_code=201)
def create_thread(
    body: ChatThreadCreateIn | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatThread:
    title = (body.title.strip() if body and body.title else None) or "New chat"
    thread = ChatThread(user_id=user.id, title=title[:255])
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread


@router.delete("/threads/{thread_id}", status_code=204)
def delete_thread(
    thread_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    thread = _get_owned_thread(db, thread_id, user)
    db.delete(thread)
    db.commit()


@router.get("/threads/{thread_id}/messages", response_model=ChatMessageListOut)
def list_messages(
    thread_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatMessageListOut:
    _get_owned_thread(db, thread_id, user)
    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.asc())
    ).all()
    return ChatMessageListOut(
        items=[ChatMessageOut.model_validate(m) for m in messages]
    )


@router.post("/threads/{thread_id}/messages", response_model=ChatTurnOut)
def post_message(
    thread_id: uuid.UUID,
    body: ChatMessageCreateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatTurnOut:
    thread = _get_owned_thread(db, thread_id, user)
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="Message content is required")

    existing = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.asc())
    ).all()
    history = [HistoryMessage(role=m.role, content=m.content) for m in existing]

    try:
        turn = run_turn(history, content)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Chat model request failed",
        ) from exc

    now = datetime.now(timezone.utc)
    user_msg = ChatMessage(thread_id=thread.id, role="user", content=content)
    assistant_msg = ChatMessage(
        thread_id=thread.id,
        role="assistant",
        content=turn.content,
        thinking=turn.thinking or None,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    if thread.title == "New chat" and not existing:
        thread.title = _title_from_content(content)
    thread.updated_at = now
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return ChatTurnOut(
        user_message=ChatMessageOut.model_validate(user_msg),
        assistant_message=ChatMessageOut.model_validate(assistant_msg),
    )

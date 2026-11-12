import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatThreadOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatThreadListOut(BaseModel):
    items: list[ChatThreadOut]


class ChatThreadCreateIn(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ChatMessageOut(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str
    thinking: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessageListOut(BaseModel):
    items: list[ChatMessageOut]


class ChatMessageCreateIn(BaseModel):
    content: str = Field(min_length=1, max_length=16000)


class ChatTurnOut(BaseModel):
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut

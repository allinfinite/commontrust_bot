from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeUser:
    id: int
    username: str | None = None
    full_name: str = "User"


@dataclass
class FakeChat:
    id: int
    type: str = "group"  # "private" or "group"/"supergroup"
    title: str | None = "Group"


@dataclass
class FakeMessage:
    text: str
    from_user: FakeUser
    chat: FakeChat
    reply_to_message: FakeMessage | None = None
    answers: list[dict[str, Any]] = field(default_factory=list)
    message_id: int = 0

    async def answer(self, text: str, **kwargs: Any) -> None:
        self.answers.append({"text": text, **kwargs})


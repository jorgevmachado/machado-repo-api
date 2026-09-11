from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database.base import table_registry
from app.models.enums import GenderEnum, StatusEnum, RoleEnum


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@table_registry.mapped_as_dataclass
class User:
    __tablename__ = 'users'

    # Required fields (no defaults) — must come first in __init__
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    gender: Mapped[GenderEnum] = mapped_column(
        SAEnum(GenderEnum, name='genderenum'), nullable=False
    )
    password: Mapped[str] = mapped_column(String, nullable=False)
    date_of_birth: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Optional fields with defaults
    status: Mapped[StatusEnum] = mapped_column(
        SAEnum(StatusEnum, name='statusenum'),
        nullable=False,
        default=StatusEnum.INACTIVE,
    )
    role: Mapped[RoleEnum] = mapped_column(
        SAEnum(RoleEnum, name='roleenum'),
        nullable=False,
        default=RoleEnum.USER,
    )

    total_authentications: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    authentication_success: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    authentication_failures: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    last_authentication_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    

    # Auto-generated / server-managed — excluded from __init__
    id: Mapped[UUID] = mapped_column(primary_key=True, default_factory=uuid4, init=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default_factory=_utcnow, init=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, init=False
    )

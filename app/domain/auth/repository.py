from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select, update as sa_update

from app.core.repository.base import BaseRepository
from app.models.enums import StatusEnum
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.scalar(select(User).where(User.email == email))
        return result

    async def get_by_username(self, username: str) -> User | None:
        result = await self.session.scalar(
            select(User).where(User.username == username)
        )
        return result

    async def get_by_email_or_username(self, credential: str) -> User | None:
        result = await self.session.scalar(
            select(User).where(
                or_(User.email == credential, User.username == credential)
            )
        )
        return result

    async def create(self, data: dict) -> User:
        user = User(**data)
        return await self.save(user)

    async def update_auth_success(self, user_id: UUID) -> None:
        now = _utcnow()
        await self.session.execute(
            sa_update(User)
            .where(User.id == user_id)
            .values(
                total_authentications=User.total_authentications + 1,
                authentication_success=User.authentication_success + 1,
                last_authentication_at=now,
                updated_at=now,
            )
        )
        await self.session.commit()

    async def update_auth_failure(self, user_id: UUID) -> None:
        now = _utcnow()
        await self.session.execute(
            sa_update(User)
            .where(User.id == user_id)
            .values(
                total_authentications=User.total_authentications + 1,
                authentication_failures=User.authentication_failures + 1,
                updated_at=now,
            )
        )
        await self.session.commit()

    async def update_status(self, user_id: UUID, status: StatusEnum) -> None:
        now = _utcnow()
        await self.session.execute(
            sa_update(User)
            .where(User.id == user_id)
            .values(status=status, updated_at=now)
        )
        await self.session.commit()

    async def soft_delete(self, user_id: UUID) -> None:
        await self.session.execute(
            sa_update(User).where(User.id == user_id).values(deleted_at=_utcnow())
        )
        await self.session.commit()

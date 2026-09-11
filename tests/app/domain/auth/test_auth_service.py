from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.domain.auth.repository import UserRepository
from app.domain.auth.schema import LoginSchema, RegisterSchema
from app.domain.auth.service import AuthService
from app.models.enums import GenderEnum, StatusEnum, RoleEnum


def build_register_schema() -> RegisterSchema:
    return RegisterSchema(
        name='Ash Ketchum',
        email='ash@example.com',
        username='ash',
        gender=GenderEnum.MALE,
        date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
        password='pikachu123',
    )


class TestAuthSchema:
    def test_register_schema_rejects_short_password(self):
        with pytest.raises(ValidationError):
            RegisterSchema(
                name='Ash',
                email='ash@example.com',
                username='ash',
                gender=GenderEnum.MALE,
                date_of_birth=datetime(1990, 1, 1, tzinfo=timezone.utc),
                password='short',
            )


class TestUserRepository:
    @staticmethod
    @pytest.mark.asyncio
    async def test_get_by_variants_delegate_to_scalar():
        session = AsyncMock()
        repository = UserRepository(session=session)

        await repository.get_by_email('ash@example.com')
        await repository.get_by_username('ash')
        await repository.get_by_email_or_username('ash')

        assert session.scalar.await_count == 3

    @staticmethod
    @pytest.mark.asyncio
    async def test_create_builds_user_and_delegates_to_save():
        session = AsyncMock()
        repository = UserRepository(session=session)
        expected = SimpleNamespace(id=uuid4())
        repository.save = AsyncMock(return_value=expected)

        result = await repository.create(
            build_register_schema().model_dump() | {'status': StatusEnum.INCOMPLETE}
        )

        assert result is expected
        repository.save.assert_awaited_once()

    @staticmethod
    @pytest.mark.asyncio
    async def test_update_methods_execute_and_commit():
        session = AsyncMock()
        repository = UserRepository(session=session)
        user_id = uuid4()

        await repository.update_auth_success(user_id)
        await repository.update_auth_failure(user_id)
        await repository.update_status(user_id, StatusEnum.ACTIVE)
        await repository.soft_delete(user_id)

        assert session.execute.await_count == 4
        assert session.commit.await_count == 4


class TestAuthService:
    @staticmethod
    @pytest.mark.asyncio
    async def test_register_rejects_existing_email():
        repository = AsyncMock()
        repository.get_by_email.return_value = object()
        service = AuthService(repository=repository, trainer_repository=AsyncMock())

        with pytest.raises(HTTPException) as exc_info:
            await service.register(build_register_schema())

        assert exc_info.value.status_code == HTTPStatus.CONFLICT
        assert exc_info.value.detail == 'Email already registered'

    @staticmethod
    @pytest.mark.asyncio
    async def test_register_rejects_existing_username():
        repository = AsyncMock()
        repository.get_by_email.return_value = None
        repository.get_by_username.return_value = object()
        service = AuthService(repository=repository, trainer_repository=AsyncMock())

        with pytest.raises(HTTPException) as exc_info:
            await service.register(build_register_schema())

        assert exc_info.value.status_code == HTTPStatus.CONFLICT
        assert exc_info.value.detail == 'Username already taken'

    @staticmethod
    @pytest.mark.asyncio
    async def test_register_creates_hashed_user(monkeypatch):
        repository = AsyncMock()
        repository.get_by_email.return_value = None
        repository.get_by_username.return_value = None
        created = SimpleNamespace(id=uuid4())
        repository.create.return_value = created
        monkeypatch.setattr('app.domain.auth.service.get_password_hash', lambda _: 'hashed-password')
        service = AuthService(repository=repository, trainer_repository=AsyncMock())

        result = await service.register(build_register_schema())

        assert result is created
        repository.create.assert_awaited_once()
        payload = repository.create.await_args.args[0]
        assert payload['password'] == 'hashed-password'
        assert payload['status'] == StatusEnum.ACTIVE

    @staticmethod
    @pytest.mark.asyncio
    async def test_login_rejects_missing_user():
        repository = AsyncMock()
        repository.get_by_email_or_username.return_value = None
        service = AuthService(repository=repository, trainer_repository=AsyncMock())

        with pytest.raises(HTTPException) as exc_info:
            await service.login(LoginSchema(credential='ash', password='pikachu123'))

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        assert exc_info.value.detail == 'Invalid credentials'

    @staticmethod
    @pytest.mark.asyncio
    async def test_login_rejects_invalid_password(monkeypatch):
        user = SimpleNamespace(id=uuid4(), password='hashed')
        repository = AsyncMock()
        repository.get_by_email_or_username.return_value = user
        monkeypatch.setattr('app.domain.auth.service.verify_password', lambda *_: False)
        service = AuthService(repository=repository, trainer_repository=AsyncMock())

        with pytest.raises(HTTPException) as exc_info:
            await service.login(LoginSchema(credential='ash', password='bad-password'))

        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED
        repository.update_auth_failure.assert_awaited_once_with(user.id)

    @staticmethod
    @pytest.mark.asyncio
    async def test_login_returns_token_for_valid_user(monkeypatch):
        user = SimpleNamespace(id=uuid4(), password='hashed')
        repository = AsyncMock()
        repository.get_by_email_or_username.return_value = user
        monkeypatch.setattr('app.domain.auth.service.verify_password', lambda *_: True)
        monkeypatch.setattr(
            'app.domain.auth.service.create_access_token',
            lambda payload: f"token-{payload['sub']}",
        )
        service = AuthService(repository=repository, trainer_repository=AsyncMock())

        result = await service.login(LoginSchema(credential='ash', password='pikachu123'))

        assert result.access_token == f'token-{user.id}'
        assert result.token_type == 'bearer'
        repository.update_auth_success.assert_awaited_once_with(user.id)

    @staticmethod
    @pytest.mark.asyncio
    async def test_me_loads_through_repository():
        user_id = uuid4()        
        current_user = SimpleNamespace(
            id=user_id,
            name='Ash',
            email='ash@example.com',            
            username='ash',
            role=RoleEnum.USER,
            status=StatusEnum.ACTIVE,
            created_at=datetime.now(timezone.utc),
        )
        trainer_repository = AsyncMock()    
        service = AuthService(repository=AsyncMock(), trainer_repository=trainer_repository)

        result = await service.me(current_user)

        trainer_repository.get_by_user_id.assert_awaited_once_with(user_id)
        assert result.id == user_id        

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.domain.auth.route import get_auth_service, login, me, register
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


class TestAuthRoutes:
    @staticmethod
    def test_get_auth_service_builds_service():
        service = get_auth_service(AsyncMock())
        assert isinstance(service, AuthService)

    @staticmethod
    @pytest.mark.asyncio
    async def test_register_route_returns_service_result():
        service = AsyncMock()
        data = build_register_schema()
        expected = SimpleNamespace(id=uuid4())
        service.register.return_value = expected

        result = await register(data, service=service)

        assert result is expected

    @staticmethod
    @pytest.mark.asyncio
    async def test_login_route_returns_token_payload():
        service = AsyncMock()
        service.login.return_value = SimpleNamespace(access_token='token', token_type='bearer')

        result = await login(LoginSchema(credential='ash', password='pikachu123'), service=service)

        assert result.access_token == 'token'

    @staticmethod
    @pytest.mark.asyncio
    async def test_me_route_delegates_to_service():
        current_user = SimpleNamespace(
            id=uuid4(),
            name='Ash',
            email='ash@example.com',
            username='ash',
            role=RoleEnum.USER,
            status=StatusEnum.ACTIVE,
            gender=GenderEnum.MALE,
            trainer=None,
            created_at=datetime.now(timezone.utc),
        )
        expected = SimpleNamespace(id=current_user.id)
        service = AsyncMock()
        service.me.return_value = expected

        result = await me(current_user=current_user, service=service)

        assert result is expected
        service.me.assert_awaited_once_with(current_user)

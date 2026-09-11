from datetime import datetime, timezone

from app.models.enums import GenderEnum, StatusEnum
from app.models.trainer import Trainer
from app.models.user import User


def test_user_and_trainer_model_instantiation():
    user = User(
        name='john Doe',
        email='john@doe.com',
        username='johndoe',
        gender=GenderEnum.MALE,
        status=StatusEnum.ACTIVE,
        password='secret',
        date_of_birth=datetime(1990, 7, 20, tzinfo=timezone.utc),
        total_authentications=0,
        authentication_success=0,
        authentication_failures=0,
    )
    trainer = Trainer(
        user_id=user.id,
        pokeballs=5,
        capture_rate=45,
    )

    assert user.name == 'john Doe'
    assert user.email == 'john@doe.com'
    assert user.username == 'johndoe'
    assert user.gender == GenderEnum.MALE
    assert user.status == StatusEnum.ACTIVE
    assert user.total_authentications == 0
    assert user.authentication_success == 0
    assert user.authentication_failures == 0
    assert user.created_at is not None
    assert trainer.user_id == user.id
    assert trainer.pokeballs == 5
    assert trainer.capture_rate == 45
    assert trainer.created_at is not None

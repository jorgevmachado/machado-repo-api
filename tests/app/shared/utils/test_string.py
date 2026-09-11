from app.shared.utils.string import is_valid_uuid


class TestStringIsValidUuid:
    @staticmethod
    def test_is_valid_uuid_valid():
        assert is_valid_uuid('123e4567-e89b-12d3-a456-426614174000')

    @staticmethod
    def test_is_valid_uuid_invalid():
        assert not is_valid_uuid('invalid-uuid')

    @staticmethod
    def test_is_valid_uuid_none():
        assert not is_valid_uuid(None)

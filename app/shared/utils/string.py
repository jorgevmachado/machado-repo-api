import uuid


def is_valid_uuid(value: str | None = None) -> bool:
    if not value:
        return False
    try:
        uuid_obj = uuid.UUID(value)
        return str(uuid_obj) == value
    except (ValueError, AttributeError, TypeError):
        return False

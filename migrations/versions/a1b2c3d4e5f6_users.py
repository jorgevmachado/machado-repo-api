"""add users

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-04-22 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
                DO $$ BEGIN
                    CREATE TYPE genderenum AS ENUM ('MALE', 'FEMALE', 'OTHER');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)
    op.execute("""
                  DO $$ BEGIN
                      CREATE TYPE statusenum AS ENUM ('ACTIVE','INACTIVE');
                  EXCEPTION
                      WHEN duplicate_object THEN null;
                  END $$;
              """)
    op.execute("""
                  DO $$ BEGIN
                      CREATE TYPE roleenum AS ENUM ('USER','ADMIN');
                  EXCEPTION
                      WHEN duplicate_object THEN null;
                  END $$;
              """)
    # Use raw SQL CREATE TABLE statements that reference the already-created
    # PostgreSQL ENUM types. This avoids SQLAlchemy attempting to create the
    # ENUM types again (which can raise DuplicateObject if the type exists).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id uuid PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL UNIQUE,
            gender genderenum NOT NULL,
            role roleenum NOT NULL,
            password TEXT NOT NULL,
            date_of_birth timestamptz NOT NULL,
            status statusenum NOT NULL,
            total_authentications integer,
            authentication_success integer,
            authentication_failures integer,
            last_authentication_at timestamptz,
            created_at timestamptz NOT NULL,
            updated_at timestamptz,
            deleted_at timestamptz
        );
        """
    )


def downgrade() -> None:
    op.drop_table('users')

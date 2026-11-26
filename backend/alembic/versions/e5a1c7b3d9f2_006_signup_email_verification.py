"""006_signup_email_verification (+ password reset codes, login lockout)

Revision ID: e5a1c7b3d9f2
Revises: c12d3e4f5a6b
Create Date: 2026-11-26 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5a1c7b3d9f2'
down_revision: Union[str, None] = 'c12d3e4f5a6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Auth-internal table: no restaurant_id yet (the restaurant does not exist until verified), so no RLS policy.
    op.execute("""
    CREATE TABLE IF NOT EXISTS pending_registrations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        email VARCHAR(255) NOT NULL UNIQUE,
        payload JSONB NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        code_hash VARCHAR(64) NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        last_sent_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_pending_registrations_email ON pending_registrations(email)")
    op.execute("""
    CREATE TABLE IF NOT EXISTS password_reset_codes (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        code_hash VARCHAR(64) NOT NULL,
        expires_at TIMESTAMPTZ NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        used_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_password_reset_codes_user_id ON password_reset_codes(user_id)")
    op.execute("""
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS locked_until, DROP COLUMN IF EXISTS failed_login_attempts")
    op.execute("DROP TABLE IF EXISTS password_reset_codes")
    op.execute("DROP TABLE IF EXISTS pending_registrations")

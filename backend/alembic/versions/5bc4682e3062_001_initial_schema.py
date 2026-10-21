"""001_initial_schema

Revision ID: 5bc4682e3062
Revises: 
Create Date: 2026-10-22 03:22:17.775042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bc4682e3062'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extensions & Types
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
            CREATE TYPE userrole AS ENUM ('customer', 'kitchen_staff', 'service_staff', 'cashier', 'manager');
        END IF;
    END
    $$;
    """)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tablestatus') THEN
            CREATE TYPE tablestatus AS ENUM ('available', 'occupied', 'awaiting_cleanup');
        END IF;
    END
    $$;
    """)

    # 2. Tables and Indexes (Single statements)
    op.execute("""
    CREATE TABLE IF NOT EXISTS restaurants (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name VARCHAR(255) NOT NULL,
        slug VARCHAR(100) NOT NULL UNIQUE,
        address TEXT,
        phone VARCHAR(50),
        currency VARCHAR(10) NOT NULL DEFAULT 'PKR',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_restaurants_slug ON restaurants(slug)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
        email VARCHAR(255),
        phone_number VARCHAR(50),
        hashed_password VARCHAR(255),
        role userrole NOT NULL DEFAULT 'customer',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        is_verified BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_restaurant_id ON users(restaurant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users(email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_phone_number ON users(phone_number)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_role ON users(role)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        display_name VARCHAR(100) NOT NULL,
        preferred_language VARCHAR(10) NOT NULL DEFAULT 'en',
        push_notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS tables (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
        table_number INTEGER NOT NULL,
        name VARCHAR(50),
        qr_code_token VARCHAR(100) NOT NULL UNIQUE,
        capacity INTEGER NOT NULL DEFAULT 4,
        status tablestatus NOT NULL DEFAULT 'available',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_tables_restaurant_id ON tables(restaurant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tables_qr_code_token ON tables(qr_code_token)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tables_status ON tables(status)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS menu_categories (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_menu_categories_restaurant_id ON menu_categories(restaurant_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS menu_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
        category_id UUID NOT NULL REFERENCES menu_categories(id) ON DELETE CASCADE,
        name VARCHAR(150) NOT NULL,
        description TEXT,
        price NUMERIC(10, 2) NOT NULL,
        image_url VARCHAR(500),
        is_available BOOLEAN NOT NULL DEFAULT TRUE,
        expected_prep_minutes INTEGER NOT NULL DEFAULT 15,
        kitchen_station VARCHAR(50) NOT NULL DEFAULT 'hot_kitchen',
        structured_attributes JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_menu_items_restaurant_id ON menu_items(restaurant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_menu_items_category_id ON menu_items(category_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        action VARCHAR(100) NOT NULL,
        resource_type VARCHAR(100),
        resource_id VARCHAR(100),
        details JSONB,
        ip_address VARCHAR(50),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_restaurant_id ON audit_logs(restaurant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action)")

    # 3. Alter column nullable if exists
    try:
        op.alter_column('users', 'hashed_password',
                   existing_type=sa.VARCHAR(length=255),
                   nullable=True)
    except Exception:
        pass

    # 4. PostgreSQL Row-Level Security (RLS) policies
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tables ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE menu_categories ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY")

    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_users') THEN
        CREATE POLICY tenant_isolation_users ON users
          USING (current_setting('app.current_restaurant_id', true) IS NULL OR current_setting('app.current_restaurant_id', true) = '' OR restaurant_id = NULLIF(current_setting('app.current_restaurant_id', true), '')::uuid);
      END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_tables') THEN
        CREATE POLICY tenant_isolation_tables ON tables
          USING (current_setting('app.current_restaurant_id', true) IS NULL OR current_setting('app.current_restaurant_id', true) = '' OR restaurant_id = NULLIF(current_setting('app.current_restaurant_id', true), '')::uuid);
      END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_menu_categories') THEN
        CREATE POLICY tenant_isolation_menu_categories ON menu_categories
          USING (current_setting('app.current_restaurant_id', true) IS NULL OR current_setting('app.current_restaurant_id', true) = '' OR restaurant_id = NULLIF(current_setting('app.current_restaurant_id', true), '')::uuid);
      END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_menu_items') THEN
        CREATE POLICY tenant_isolation_menu_items ON menu_items
          USING (current_setting('app.current_restaurant_id', true) IS NULL OR current_setting('app.current_restaurant_id', true) = '' OR restaurant_id = NULLIF(current_setting('app.current_restaurant_id', true), '')::uuid);
      END IF;
    END
    $$;
    """)

    op.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'tenant_isolation_audit_logs') THEN
        CREATE POLICY tenant_isolation_audit_logs ON audit_logs
          USING (current_setting('app.current_restaurant_id', true) IS NULL OR current_setting('app.current_restaurant_id', true) = '' OR restaurant_id = NULLIF(current_setting('app.current_restaurant_id', true), '')::uuid);
      END IF;
    END
    $$;
    """)


def downgrade() -> None:
    op.execute("""
    DROP POLICY IF EXISTS tenant_isolation_audit_logs ON audit_logs;
    DROP POLICY IF EXISTS tenant_isolation_menu_items ON menu_items;
    DROP POLICY IF EXISTS tenant_isolation_menu_categories ON menu_categories;
    DROP POLICY IF EXISTS tenant_isolation_tables ON tables;
    DROP POLICY IF EXISTS tenant_isolation_users ON users;

    ALTER TABLE IF EXISTS audit_logs DISABLE ROW LEVEL SECURITY;
    ALTER TABLE IF EXISTS menu_items DISABLE ROW LEVEL SECURITY;
    ALTER TABLE IF EXISTS menu_categories DISABLE ROW LEVEL SECURITY;
    ALTER TABLE IF EXISTS tables DISABLE ROW LEVEL SECURITY;
    ALTER TABLE IF EXISTS users DISABLE ROW LEVEL SECURITY;
    """)

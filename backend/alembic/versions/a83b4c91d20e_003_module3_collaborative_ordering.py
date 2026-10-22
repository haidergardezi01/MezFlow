"""003_module3_collaborative_ordering

Revision ID: a83b4c91d20e
Revises: 7c2e3f4a8b91
Create Date: 2026-10-22 17:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a83b4c91d20e'
down_revision: Union[str, None] = '7c2e3f4a8b91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums if not exist
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sessionstatus') THEN
            CREATE TYPE sessionstatus AS ENUM ('ACTIVE', 'SUBMITTING', 'COMPLETED', 'CLOSED');
        END IF;
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
            CREATE TYPE orderstatus AS ENUM ('NEW', 'CONFIRMED', 'PREPARING', 'READY', 'DISPATCHED', 'CANCELLED');
        END IF;
    END$$;
    """)

    # 2. Table: table_sessions
    op.execute("""
    CREATE TABLE IF NOT EXISTS table_sessions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
        table_id UUID NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
        session_token VARCHAR(100) NOT NULL UNIQUE,
        status sessionstatus NOT NULL DEFAULT 'ACTIVE',
        host_diner_id UUID,
        total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
        opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        closed_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_table_sessions_restaurant_id ON table_sessions(restaurant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_table_sessions_table_id ON table_sessions(table_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_table_sessions_session_token ON table_sessions(session_token)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_table_sessions_status ON table_sessions(status)")

    # 3. Table: diners
    op.execute("""
    CREATE TABLE IF NOT EXISTS diners (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id UUID NOT NULL REFERENCES table_sessions(id) ON DELETE CASCADE,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        display_name VARCHAR(50) NOT NULL,
        avatar_color VARCHAR(20) NOT NULL DEFAULT '#F59E0B',
        client_session_id VARCHAR(100) NOT NULL,
        is_host BOOLEAN NOT NULL DEFAULT FALSE,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_diners_session_id ON diners(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_diners_client_session_id ON diners(client_session_id)")

    # 4. Table: cart_items
    op.execute("""
    CREATE TABLE IF NOT EXISTS cart_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id UUID NOT NULL REFERENCES table_sessions(id) ON DELETE CASCADE,
        item_id UUID NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
        diner_id UUID NOT NULL REFERENCES diners(id) ON DELETE CASCADE,
        quantity INTEGER NOT NULL DEFAULT 1,
        special_instructions VARCHAR(255),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cart_items_session_id ON cart_items(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cart_items_item_id ON cart_items(item_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cart_items_diner_id ON cart_items(diner_id)")

    # 5. Table: cart_item_modifiers
    op.execute("""
    CREATE TABLE IF NOT EXISTS cart_item_modifiers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        cart_item_id UUID NOT NULL REFERENCES cart_items(id) ON DELETE CASCADE,
        modifier_option_id UUID NOT NULL REFERENCES modifier_options(id) ON DELETE CASCADE,
        option_name_cached VARCHAR(100),
        price_delta_cached NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cart_item_modifiers_cart_item_id ON cart_item_modifiers(cart_item_id)")

    # 6. Table: orders
    op.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
        table_id UUID NOT NULL REFERENCES tables(id) ON DELETE CASCADE,
        session_id UUID REFERENCES table_sessions(id) ON DELETE SET NULL,
        order_number INTEGER NOT NULL,
        display_number VARCHAR(20) NOT NULL,
        status orderstatus NOT NULL DEFAULT 'NEW',
        subtotal NUMERIC(10, 2) NOT NULL,
        tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
        total_amount NUMERIC(10, 2) NOT NULL,
        placed_by_diner_id UUID REFERENCES diners(id) ON DELETE SET NULL,
        notes TEXT,
        placed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_restaurant_id ON orders(restaurant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_table_id ON orders(table_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_session_id ON orders(session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_order_number ON orders(order_number)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_orders_status ON orders(status)")

    # 7. Table: order_items
    op.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        item_id UUID REFERENCES menu_items(id) ON DELETE SET NULL,
        diner_id UUID REFERENCES diners(id) ON DELETE SET NULL,
        item_name VARCHAR(150) NOT NULL,
        kitchen_station VARCHAR(50) NOT NULL DEFAULT 'hot_kitchen',
        quantity INTEGER NOT NULL DEFAULT 1,
        unit_price NUMERIC(10, 2) NOT NULL,
        total_price NUMERIC(10, 2) NOT NULL,
        special_instructions VARCHAR(255),
        status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_order_items_order_id ON order_items(order_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_order_items_status ON order_items(status)")

    # 8. Table: order_item_modifiers
    op.execute("""
    CREATE TABLE IF NOT EXISTS order_item_modifiers (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        order_item_id UUID NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
        modifier_option_id UUID REFERENCES modifier_options(id) ON DELETE SET NULL,
        option_name VARCHAR(100) NOT NULL,
        price_delta NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_order_item_modifiers_order_item_id ON order_item_modifiers(order_item_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS order_item_modifiers")
    op.execute("DROP TABLE IF EXISTS order_items")
    op.execute("DROP TABLE IF EXISTS orders")
    op.execute("DROP TABLE IF EXISTS cart_item_modifiers")
    op.execute("DROP TABLE IF EXISTS cart_items")
    op.execute("DROP TABLE IF EXISTS diners")
    op.execute("DROP TABLE IF EXISTS table_sessions")
    op.execute("DROP TYPE IF EXISTS orderstatus")
    op.execute("DROP TYPE IF EXISTS sessionstatus")

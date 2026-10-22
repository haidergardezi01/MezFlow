"""002_module2_menu_modifiers

Revision ID: 7c2e3f4a8b91
Revises: 5bc4682e3062
Create Date: 2026-10-22 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c2e3f4a8b91'
down_revision: Union[str, None] = '5bc4682e3062'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update menu_categories with Urdu fields and icon_name
    op.execute("ALTER TABLE menu_categories ADD COLUMN IF NOT EXISTS name_ur VARCHAR(100)")
    op.execute("ALTER TABLE menu_categories ADD COLUMN IF NOT EXISTS description_ur TEXT")
    op.execute("ALTER TABLE menu_categories ADD COLUMN IF NOT EXISTS icon_name VARCHAR(50)")

    # 2. Update menu_items with Urdu fields, dietary_tags, and sort_order
    op.execute("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS name_ur VARCHAR(150)")
    op.execute("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS description_ur TEXT")
    op.execute("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS dietary_tags JSONB DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE menu_items ADD COLUMN IF NOT EXISTS sort_order INTEGER NOT NULL DEFAULT 0")

    # 3. Create item_modifier_groups table
    op.execute("""
    CREATE TABLE IF NOT EXISTS item_modifier_groups (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        restaurant_id UUID NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
        item_id UUID NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        name_ur VARCHAR(100),
        selection_type VARCHAR(20) NOT NULL DEFAULT 'single',
        min_selections INTEGER NOT NULL DEFAULT 0,
        max_selections INTEGER NOT NULL DEFAULT 1,
        is_required BOOLEAN NOT NULL DEFAULT FALSE,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_item_modifier_groups_restaurant_id ON item_modifier_groups(restaurant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_item_modifier_groups_item_id ON item_modifier_groups(item_id)")

    # 4. Create modifier_options table
    op.execute("""
    CREATE TABLE IF NOT EXISTS modifier_options (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        group_id UUID NOT NULL REFERENCES item_modifier_groups(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        name_ur VARCHAR(100),
        price_delta NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
        is_default BOOLEAN NOT NULL DEFAULT FALSE,
        is_available BOOLEAN NOT NULL DEFAULT TRUE,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_modifier_options_group_id ON modifier_options(group_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS modifier_options")
    op.execute("DROP TABLE IF EXISTS item_modifier_groups")
    op.execute("ALTER TABLE menu_items DROP COLUMN IF EXISTS sort_order")
    op.execute("ALTER TABLE menu_items DROP COLUMN IF EXISTS dietary_tags")
    op.execute("ALTER TABLE menu_items DROP COLUMN IF EXISTS description_ur")
    op.execute("ALTER TABLE menu_items DROP COLUMN IF EXISTS name_ur")
    op.execute("ALTER TABLE menu_categories DROP COLUMN IF EXISTS icon_name")
    op.execute("ALTER TABLE menu_categories DROP COLUMN IF EXISTS description_ur")
    op.execute("ALTER TABLE menu_categories DROP COLUMN IF EXISTS name_ur")

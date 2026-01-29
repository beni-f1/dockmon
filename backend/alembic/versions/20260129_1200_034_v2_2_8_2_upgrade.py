"""v2.2.8-2 upgrade - Container visibility filtering per user

Revision ID: 034_v2_2_8_2
Revises: 033_v2_2_8_1
Create Date: 2026-01-29

CHANGES IN v2.2.8-2:
- feat: Container visibility filtering based on tags
  - visible_tags: Whitelist - user only sees containers with these tags
  - hidden_tags: Blacklist - containers with these tags are hidden from user
  - If no tags defined, user sees all containers (backward compatible)
  - hidden_tags takes precedence over visible_tags

SCHEMA CHANGES:
- users: Add visible_tags column (JSON array of tag strings)
- users: Add hidden_tags column (JSON array of tag strings)
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '034_v2_2_8_2'
down_revision = '033_v2_2_8_1'
branch_labels = None
depends_on = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade():
    """Add container visibility tag columns to users table"""

    if table_exists('users'):
        # Add visible_tags column if it doesn't exist
        if not column_exists('users', 'visible_tags'):
            op.add_column('users', sa.Column('visible_tags', sa.Text(), nullable=True))
        
        # Add hidden_tags column if it doesn't exist
        if not column_exists('users', 'hidden_tags'):
            op.add_column('users', sa.Column('hidden_tags', sa.Text(), nullable=True))

    # Update app_version
    if table_exists('global_settings'):
        op.execute(
            sa.text("UPDATE global_settings SET app_version = :version WHERE id = :id")
            .bindparams(version='2.2.8-2', id=1)
        )


def downgrade():
    """Remove container visibility tag columns"""

    if table_exists('users'):
        if column_exists('users', 'visible_tags'):
            op.drop_column('users', 'visible_tags')
        if column_exists('users', 'hidden_tags'):
            op.drop_column('users', 'hidden_tags')

    if table_exists('global_settings'):
        # Downgrade app_version
        op.execute(
            sa.text("UPDATE global_settings SET app_version = :version WHERE id = :id")
            .bindparams(version='2.2.8-1', id=1)
        )

"""v2.2.9 upgrade - Multi-user role-based access control

Revision ID: 033_v2_2_9
Revises: 032_v2_2_8
Create Date: 2026-01-28

CHANGES IN v2.2.9:
- feat: Multi-user support with role-based access control (RBAC)
  - Three roles: admin, user, readonly
  - Admin: Full access - can manage users, hosts, containers, and all settings
  - User: Standard access - can manage containers and hosts but not users
  - Readonly: View-only access - can only view data, no modifications
- feat: User management API for administrators
  - Create, update, delete users
  - Password reset functionality
  - Role assignment
- fix: Ensure all existing users have admin role (backward compatibility)

SCHEMA CHANGES:
- users: Ensure role column has default value 'admin' for existing users
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '033_v2_2_9'
down_revision = '032_v2_2_8'
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
    """Ensure all existing users have admin role for backward compatibility"""

    if table_exists('users'):
        # Ensure role column exists (it should from the model, but check anyway)
        if not column_exists('users', 'role'):
            op.add_column('users', sa.Column('role', sa.Text(), nullable=False, server_default='admin'))
        
        # Set all existing users without a role to 'admin' for backward compatibility
        # This ensures users upgrading from previous versions maintain admin access
        op.execute(sa.text("""
            UPDATE users
            SET role = 'admin'
            WHERE role IS NULL OR role = ''
        """))

    # Update app_version
    if table_exists('global_settings'):
        op.execute(
            sa.text("UPDATE global_settings SET app_version = :version WHERE id = :id")
            .bindparams(version='2.2.9', id=1)
        )


def downgrade():
    """Downgrade - no schema changes to revert, just version"""

    if table_exists('global_settings'):
        # Downgrade app_version
        op.execute(
            sa.text("UPDATE global_settings SET app_version = :version WHERE id = :id")
            .bindparams(version='2.2.8', id=1)
        )

"""pk fix for phases and works

Revision ID: 5d55bcdaf8b5
Revises: 7fb13a243f5c
Create Date: 2026-09-09 12:33:39.424475

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '5d55bcdaf8b5'
down_revision = '7fb13a243f5c'
branch_labels = None
depends_on = None


# Tables whose `id` was mistakenly created as SERIAL. These IDs are sourced
# from EPIC.track via a cron dump and must be inserted verbatim, so the
# auto-increment sequence default has to be removed.
TABLES = ("track_phases", "track_works")


def upgrade():
    """Convert `id` columns from SERIAL to plain integer primary keys.

    Drops the `nextval(...)` column default and the owned sequence so the
    values dumped from EPIC.track are no longer auto-incremented.
    """
    for table in TABLES:
        # Detach and drop the auto-increment default.
        op.execute(f'ALTER TABLE {table} ALTER COLUMN id DROP DEFAULT')
        # Remove the sequence that backed the SERIAL column.
        op.execute(f'DROP SEQUENCE IF EXISTS {table}_id_seq')


def downgrade():
    """Restore the SERIAL-style auto-increment default on the `id` columns."""
    for table in TABLES:
        seq_name = f'{table}_id_seq'
        op.execute(f'CREATE SEQUENCE IF NOT EXISTS {seq_name} OWNED BY {table}.id')
        op.execute(
            f"ALTER TABLE {table} "
            f"ALTER COLUMN id SET DEFAULT nextval('{seq_name}'::regclass)"
        )
        # Realign the sequence with the current max id so future inserts don't collide.
        op.execute(
            f"SELECT setval('{seq_name}', "
            f"COALESCE((SELECT MAX(id) FROM {table}), 1), true)"
        )

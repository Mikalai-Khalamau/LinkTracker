from pathlib import Path
from alembic import op

revision = "001_create_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Читает SQL файл и выполняет его в транзакции миграции."""
    sql_file = Path(__file__).parent / "001_create_schema.sql"
    if not sql_file.exists():
        raise FileNotFoundError(f"SQL migration file not found: {sql_file}")

    op.execute(sql_file.read_text())


def downgrade() -> None:
    """Откат миграции."""
    op.execute("DROP TABLE IF EXISTS chat_links CASCADE;")
    op.execute("DROP TABLE IF EXISTS links CASCADE;")
    op.execute("DROP TABLE IF EXISTS chats CASCADE;")

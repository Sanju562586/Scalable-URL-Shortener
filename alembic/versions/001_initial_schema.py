"""Initial schema — creates api_keys, urls, and click_events tables."""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("owner", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "urls",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("short_code", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column(
            "api_key_id",
            sa.Integer(),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "click_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "url_id",
            sa.BigInteger(),
            sa.ForeignKey("urls.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("referer", sa.Text(), nullable=True),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column(
            "clicked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("click_events")
    op.drop_table("urls")
    op.drop_table("api_keys")

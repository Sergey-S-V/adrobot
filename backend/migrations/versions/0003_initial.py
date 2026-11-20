"""Initial schema for the campaign creator and offer editor."""

import sqlalchemy as sa
from alembic import op

# Keep the revision of the already migrated local database.
revision = "0003"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("keitaro_id", sa.BigInteger(), unique=True, nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
    )
    op.create_table(
        "streams",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("campaign_id", sa.Uuid(), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("keitaro_id", sa.BigInteger(), unique=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("schema", sa.String(64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_index("ix_streams_campaign_position", "streams", ["campaign_id", "position"])
    op.create_table(
        "stream_offers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("stream_id", sa.Uuid(), sa.ForeignKey("streams.id"), nullable=False),
        sa.Column("keitaro_offer_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("base_state", sa.String(32), nullable=True),
        sa.Column("draft_state", sa.String(32), nullable=True),
        sa.Column("base_share", sa.SmallInteger(), nullable=False),
        sa.Column("draft_share", sa.SmallInteger(), nullable=False),
        sa.Column("base_pin_share", sa.SmallInteger(), nullable=True),
        sa.Column("draft_pin_share", sa.SmallInteger(), nullable=True),
        sa.Column("ever_published", sa.Boolean(), nullable=False),
        sa.Column("allocation_order", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("stream_id", "keitaro_offer_id", name="uq_stream_offer"),
        sa.UniqueConstraint("stream_id", "allocation_order", name="uq_stream_order"),
        sa.CheckConstraint(
            "base_share BETWEEN 0 AND 100 AND draft_share BETWEEN 0 AND 100", name="ck_share_range"
        ),
        sa.CheckConstraint(
            "base_state IS NULL OR base_state IN ('active', 'disabled')", name="ck_base_state"
        ),
        sa.CheckConstraint(
            "draft_state IS NULL OR draft_state IN ('active', 'disabled')", name="ck_draft_state"
        ),
        sa.CheckConstraint(
            "base_pin_share IS NULL OR (base_state IS NOT NULL AND base_state = 'active' AND base_pin_share BETWEEN 0 AND 100 AND base_pin_share = base_share)",
            name="ck_base_pin",
        ),
        sa.CheckConstraint(
            "draft_pin_share IS NULL OR (draft_state IS NOT NULL AND draft_state = 'active' AND draft_pin_share BETWEEN 0 AND 100 AND draft_pin_share = draft_share)",
            name="ck_draft_pin",
        ),
        sa.CheckConstraint(
            "base_state IS NOT NULL OR (base_share = 0 AND base_pin_share IS NULL)",
            name="ck_base_removed",
        ),
        sa.CheckConstraint(
            "draft_state IS NOT NULL OR (draft_share = 0 AND draft_pin_share IS NULL)",
            name="ck_draft_removed",
        ),
    )
    op.create_index("ix_stream_offers_stream_id", "stream_offers", ["stream_id"])


def downgrade() -> None:
    op.drop_table("stream_offers")
    op.drop_table("streams")
    op.drop_table("campaigns")

"""add_webhook_provider_column

webhook_endpoints 新增 provider 列。后台 Webhook 列表一直把 Provider 当成
一等公民展示（GitHub / 飞书 / 邮件 / 通用），但后端从未声明该字段，
Pydantic 与 FastAPI 各自把它静默丢弃 —— 也就是保存后永远回落成默认值。
本次把列真正落到库里，投递逻辑仍对所有 provider 一致。

Revision ID: 20260926_000001
Revises: 20260917_000001
Create Date: 2026-09-26 18:09:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260926_000001"
down_revision: Union[str, None] = "20260917_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：webhook_endpoints 增加 provider（默认 generic）。"""
    with op.batch_alter_table("webhook_endpoints", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "provider",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'generic'"),
            )
        )


def downgrade() -> None:
    """回退：删除 provider 列。"""
    with op.batch_alter_table("webhook_endpoints", schema=None) as batch_op:
        batch_op.drop_column("provider")

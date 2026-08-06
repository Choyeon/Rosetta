"""merge 4 heads

Revision ID: 5018757acef3
Revises: 20260731_000005, 20260804_000002, 3e16398564fc, b7f2a9d3c4e1
Create Date: 2026-08-06 04:48:16.059146

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5018757acef3'
down_revision: Union[str, None] = ('20260731_000005', '20260804_000002', '3e16398564fc', 'b7f2a9d3c4e1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级数据库"""
    pass


def downgrade() -> None:
    """回退数据库"""
    pass

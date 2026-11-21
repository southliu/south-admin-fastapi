"""Create the managed schema and operational indexes."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20261121_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def _column_names(table_name: str) -> set[str]:
    columns = inspect(op.get_bind()).get_columns(table_name)
    return {column["name"] for column in columns}


def _index_names(table_name: str) -> set[str]:
    indexes = inspect(op.get_bind()).get_indexes(table_name)
    return {index["name"] for index in indexes}


def _ensure_index(
    name: str,
    table_name: str,
    columns: list[str],
) -> None:
    if name not in _index_names(table_name):
        op.create_index(name, table_name, columns)


def _base_columns() -> list[sa.Column[object]]:
    return [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("create_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("update_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    tables = _table_names()
    if "sys_user" not in tables:
        op.create_table(
            "sys_user",
            *_base_columns(),
            sa.Column("username", sa.String(100), nullable=False, unique=True),
            sa.Column("password", sa.String(255), nullable=False),
            sa.Column("name", sa.String(100)),
            sa.Column("phone", sa.String(20)),
            sa.Column("email", sa.String(100)),
            sa.Column(
                "status", sa.Integer(), nullable=False, server_default="1"
            ),
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "is_deleted",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
        )
    elif "token_version" not in _column_names("sys_user"):
        op.add_column(
            "sys_user",
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    tables = _table_names()
    if "sys_role" not in tables:
        op.create_table(
            "sys_role",
            *_base_columns(),
            sa.Column("name", sa.String(50), nullable=False, unique=True),
            sa.Column("description", sa.Text()),
            sa.Column(
                "is_deleted",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
        )

    tables = _table_names()
    if "sys_permission" not in tables:
        op.create_table(
            "sys_permission",
            *_base_columns(),
            sa.Column("name", sa.String(100), nullable=False, unique=True),
            sa.Column("description", sa.Text()),
            sa.Column(
                "is_deleted",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
        )

    tables = _table_names()
    if "sys_menu" not in tables:
        op.create_table(
            "sys_menu",
            *_base_columns(),
            sa.Column("label", sa.String(50), nullable=False),
            sa.Column("label_en", sa.String(50), nullable=False),
            sa.Column("icon", sa.String(100)),
            sa.Column("type", sa.Integer(), nullable=False),
            sa.Column("router", sa.String(255)),
            sa.Column(
                "order", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column(
                "state", sa.Integer(), nullable=False, server_default="1"
            ),
            sa.Column("parent_id", sa.Integer()),
            sa.Column("permission_id", sa.Integer()),
            sa.Column(
                "is_deleted",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
            sa.ForeignKeyConstraint(["parent_id"], ["sys_menu.id"]),
            sa.ForeignKeyConstraint(
                ["permission_id"],
                ["sys_permission.id"],
            ),
        )

    tables = _table_names()
    if "sys_log" not in tables:
        op.create_table(
            "sys_log",
            *_base_columns(),
            sa.Column("username", sa.String(100)),
            sa.Column("ip", sa.String(50)),
            sa.Column("method", sa.String(10)),
            sa.Column("url", sa.String(500)),
            sa.Column("params", sa.Text()),
            sa.Column("user_agent", sa.String(500)),
            sa.Column("status", sa.String(20)),
            sa.Column("error", sa.Text()),
            sa.Column(
                "latency",
                sa.BigInteger(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "type",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )

    tables = _table_names()
    if "sys_article" not in tables:
        op.create_table(
            "sys_article",
            *_base_columns(),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("author", sa.String(100)),
            sa.Column("content", sa.Text()),
            sa.Column("demo", sa.JSON()),
            sa.Column("creator", sa.String(100)),
            sa.Column("updater", sa.String(100)),
            sa.Column(
                "is_deleted",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
        )

    tables = _table_names()
    if "sys_user_role" not in tables:
        op.create_table(
            "sys_user_role",
            sa.Column("user_id", sa.Integer(), primary_key=True),
            sa.Column("role_id", sa.Integer(), primary_key=True),
            sa.ForeignKeyConstraint(["user_id"], ["sys_user.id"]),
            sa.ForeignKeyConstraint(["role_id"], ["sys_role.id"]),
        )
    if "sys_role_menu" not in tables:
        op.create_table(
            "sys_role_menu",
            sa.Column("role_id", sa.Integer(), primary_key=True),
            sa.Column("menu_id", sa.Integer(), primary_key=True),
            sa.ForeignKeyConstraint(["role_id"], ["sys_role.id"]),
            sa.ForeignKeyConstraint(["menu_id"], ["sys_menu.id"]),
        )

    _ensure_index(
        "ix_sys_user_active_status_created",
        "sys_user",
        ["is_deleted", "status", "create_at"],
    )
    _ensure_index(
        "ix_sys_role_active_created",
        "sys_role",
        ["is_deleted", "create_at"],
    )
    _ensure_index(
        "ix_sys_permission_active_created",
        "sys_permission",
        ["is_deleted", "create_at"],
    )
    _ensure_index(
        "ix_sys_menu_tree",
        "sys_menu",
        ["is_deleted", "state", "parent_id", "order"],
    )
    _ensure_index("ix_sys_log_created", "sys_log", ["create_at"])
    _ensure_index(
        "ix_sys_log_user_type_created",
        "sys_log",
        ["username", "type", "create_at"],
    )
    _ensure_index(
        "ix_sys_article_active_created",
        "sys_article",
        ["is_deleted", "create_at"],
    )


def downgrade() -> None:
    for table_name in (
        "sys_role_menu",
        "sys_user_role",
        "sys_article",
        "sys_log",
        "sys_menu",
        "sys_permission",
        "sys_role",
        "sys_user",
    ):
        if table_name in _table_names():
            op.drop_table(table_name)

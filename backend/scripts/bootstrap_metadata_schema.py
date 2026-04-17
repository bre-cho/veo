from __future__ import annotations

from typing import Dict, Tuple

from sqlalchemy import Column, Table
from sqlalchemy.sql.type_api import TypeEngine

from app.db.base import Base
from app.db.session import engine
import app.models  # noqa: F401


def _normalize_table_key(table_ref: str) -> Tuple[str | None, str]:
    cleaned = table_ref.replace('"', "")
    if "." in cleaned:
        schema, name = cleaned.rsplit(".", 1)
        return (schema or None), name
    return None, cleaned


def _table_key(schema: str | None, name: str) -> str:
    return f"{schema}.{name}" if schema else name


def _collect_missing_fk_targets() -> Dict[Tuple[str | None, str], Dict[str, TypeEngine]]:
    missing: Dict[Tuple[str | None, str], Dict[str, TypeEngine]] = {}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            for foreign_key in column.foreign_keys:
                target = foreign_key.target_fullname
                if "." not in target:
                    continue

                target_ref, target_column = target.rsplit(".", 1)
                schema, table_name = _normalize_table_key(target_ref)
                key = _table_key(schema, table_name)
                if key in Base.metadata.tables:
                    continue

                type_hint = foreign_key.parent.type
                missing.setdefault((schema, table_name), {})[target_column] = type_hint
    return missing


def _create_placeholder_table(
    schema: str | None,
    table_name: str,
    column_types: Dict[str, TypeEngine],
) -> None:
    columns = []
    for column_name, column_type in sorted(column_types.items()):
        resolved_type = column_type.copy() if hasattr(column_type, "copy") else column_type
        columns.append(
            Column(
                column_name,
                resolved_type,
                primary_key=True,
                nullable=False,
            )
        )

    if not columns:
        return

    Table(
        table_name,
        Base.metadata,
        *columns,
        schema=schema,
        extend_existing=True,
    )


def _dedupe_table_indexes() -> None:
    for table in Base.metadata.tables.values():
        seen_names = set()
        duplicated = []
        for index in list(table.indexes):
            # Keep first index object per name; drop duplicated definitions.
            if index.name and index.name in seen_names:
                duplicated.append(index)
                continue
            if index.name:
                seen_names.add(index.name)

        for index in duplicated:
            table.indexes.discard(index)


def main() -> int:
    print("Bootstrapping database schema from SQLAlchemy metadata...")

    missing_targets = _collect_missing_fk_targets()
    if missing_targets:
        print("Detected missing referenced tables. Creating placeholders...")
        for (schema, table_name), column_types in sorted(missing_targets.items()):
            full_name = _table_key(schema, table_name)
            print(f" - placeholder table: {full_name}")
            _create_placeholder_table(schema, table_name, column_types)

    _dedupe_table_indexes()

    Base.metadata.create_all(bind=engine)
    print("SQLAlchemy metadata bootstrap completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
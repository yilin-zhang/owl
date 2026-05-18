from __future__ import annotations

from typing import Any

from .store import json_text


def write_tsv(rows: list[dict[str, Any]], columns: list[str]) -> None:
    print("\t".join(columns))
    for row in rows:
        print("\t".join(tsv_cell(row.get(column, "")) for column in columns))


def tsv_cell(value: Any) -> str:
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ")


def write_json(data: Any) -> None:
    print(json_text(data), end="")


def format_text_message(message: dict[str, Any]) -> str:
    to = ",".join(message.get("to", []))
    cc = ",".join(message.get("cc", []))
    lines = [
        f"id: {message.get('id', '')}",
        f"from: {message.get('from_name') or message.get('from', '')}",
        f"to: {to}",
    ]
    if cc:
        lines.append(f"cc: {cc}")
    lines.extend([f"created_at: {message.get('created_at', '')}", "", message.get("body", "")])
    return "\n".join(lines)

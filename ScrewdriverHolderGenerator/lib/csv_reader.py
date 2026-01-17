import csv
from dataclasses import dataclass
from typing import List


@dataclass
class Tool:
    name: str
    row: int
    col: int
    handle_d_mm: float
    shaft_d_mm: float
    enabled: bool = True


def _parse_bool(value: str) -> bool:
    if value is None:
        return True
    value = value.strip()
    if value == "":
        return True
    return value not in {"0", "false", "False", "FALSE"}


def read_tools_from_csv(csv_path: str) -> List[Tool]:
    with open(csv_path, newline="", encoding="utf-8-sig") as csvfile:
        reader = csv.DictReader(csvfile)
        if reader.fieldnames is None:
            raise ValueError("CSV must include a header row.")

        required = {"name", "row", "col", "handle_d_mm", "shaft_d_mm"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(f"CSV missing required columns: {', '.join(sorted(missing))}")

        tools: List[Tool] = []
        for index, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            enabled = _parse_bool(row.get("enabled"))
            if not enabled:
                continue
            tool = Tool(
                name=name,
                row=int(row.get("row")),
                col=int(row.get("col")),
                handle_d_mm=float(row.get("handle_d_mm")),
                shaft_d_mm=float(row.get("shaft_d_mm")),
                enabled=True,
            )
            tools.append(tool)
        return tools

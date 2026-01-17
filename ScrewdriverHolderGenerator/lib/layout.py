from dataclasses import dataclass
from typing import Dict, List, Tuple

from .csv_reader import Tool


@dataclass
class Layout:
    col_widths: Dict[int, float]
    row_depths: Dict[int, float]
    centers: Dict[Tuple[int, int], Tuple[float, float]]
    part_width_mm: float
    part_depth_mm: float
    max_row: int
    max_col: int


def compute_layout(tools: List[Tool], params: Dict[str, float]) -> Layout:
    col_max: Dict[int, float] = {}
    row_max: Dict[int, float] = {}

    for tool in tools:
        col_max[tool.col] = max(col_max.get(tool.col, 0.0), tool.handle_d_mm)
        row_max[tool.row] = max(row_max.get(tool.row, 0.0), tool.handle_d_mm)

    col_widths: Dict[int, float] = {}
    for col, max_handle in col_max.items():
        col_widths[col] = max(
            max_handle + params["handle_x_pad"],
            max_handle + params["min_web"],
        )

    row_depths: Dict[int, float] = {}
    for row, max_handle in row_max.items():
        row_depths[row] = max(
            max_handle + params["handle_y_pad"],
            max_handle + params["min_web"],
        )

    max_col = max(col_widths.keys())
    max_row = max(row_depths.keys())

    for col in range(max_col + 1):
        col_widths.setdefault(col, params["min_web"])
    for row in range(max_row + 1):
        row_depths.setdefault(row, params["min_web"])

    def _prefix_sum(values: Dict[int, float], idx: int) -> float:
        return sum(values[i] for i in range(idx))

    centers: Dict[Tuple[int, int], Tuple[float, float]] = {}
    x0 = params["edge_margin_x"]
    y0 = params["edge_margin_y"]

    for tool in tools:
        x_center = x0 + _prefix_sum(col_widths, tool.col) + col_widths[tool.col] / 2
        y_center = y0 + _prefix_sum(row_depths, tool.row) + row_depths[tool.row] / 2
        centers[(tool.row, tool.col)] = (x_center, y_center)

    part_width_mm = 2 * params["edge_margin_x"] + sum(
        col_widths[i] for i in range(max_col + 1)
    )
    part_depth_mm = 2 * params["edge_margin_y"] + sum(
        row_depths[i] for i in range(max_row + 1)
    )

    return Layout(
        col_widths=col_widths,
        row_depths=row_depths,
        centers=centers,
        part_width_mm=part_width_mm,
        part_depth_mm=part_depth_mm,
        max_row=max_row,
        max_col=max_col,
    )

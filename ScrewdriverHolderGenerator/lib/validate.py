from typing import Dict, List, Tuple

from .csv_reader import Tool


def validate_tools(tools: List[Tool]) -> None:
    if not tools:
        raise ValueError("No enabled tools found in CSV.")

    seen: Dict[Tuple[int, int], Tool] = {}
    for tool in tools:
        if not tool.name:
            raise ValueError("Tool name must be non-empty.")
        if tool.row < 0 or tool.col < 0:
            raise ValueError(f"Invalid row/col for tool '{tool.name}'.")
        if tool.handle_d_mm <= 0 or tool.shaft_d_mm <= 0:
            raise ValueError(f"Invalid diameters for tool '{tool.name}'.")
        key = (tool.row, tool.col)
        if key in seen:
            raise ValueError(
                f"Duplicate row/col ({tool.row}, {tool.col}) for '{tool.name}' and '{seen[key].name}'."
            )
        seen[key] = tool


def validate_mount_offsets(
    params: Dict[str, float],
    part_width_mm: float,
    part_depth_mm: float,
) -> None:
    hole_radius = params["mount_hole_d"] / 2
    min_web = params["min_web"]
    offset_x = params["mount_hole_edge_offset_x"]
    offset_y = params["mount_hole_edge_offset_y"]

    if offset_x <= hole_radius + min_web:
        raise ValueError("Mount hole X offset too small for edge clearance.")
    if offset_y <= hole_radius + min_web:
        raise ValueError("Mount hole Y offset too small for edge clearance.")

    if offset_x >= part_width_mm - hole_radius - min_web:
        raise ValueError("Mount hole X offset places holes outside part.")
    if offset_y >= part_depth_mm - hole_radius - min_web:
        raise ValueError("Mount hole Y offset places holes outside part.")


def validate_params(params: Dict[str, float]) -> None:
    if params["base_thickness"] < params["min_floor_thickness"]:
        raise ValueError("Base thickness must be >= min_floor_thickness.")


def validate_spacing(
    tools: List[Tool],
    centers: Dict[Tuple[int, int], Tuple[float, float]],
    params: Dict[str, float],
) -> None:
    min_web = params["min_web"]
    for i, tool_a in enumerate(tools):
        for tool_b in tools[i + 1 :]:
            if tool_a.row == tool_b.row:
                xa, _ = centers[(tool_a.row, tool_a.col)]
                xb, _ = centers[(tool_b.row, tool_b.col)]
                min_dist = (tool_a.shaft_d_mm + tool_b.shaft_d_mm) / 2 + min_web
                if abs(xa - xb) < min_dist:
                    raise ValueError(
                        f"Hole spacing too tight between '{tool_a.name}' and '{tool_b.name}'."
                    )
            if tool_a.col == tool_b.col:
                _, ya = centers[(tool_a.row, tool_a.col)]
                _, yb = centers[(tool_b.row, tool_b.col)]
                min_dist = (tool_a.shaft_d_mm + tool_b.shaft_d_mm) / 2 + min_web
                if abs(ya - yb) < min_dist:
                    raise ValueError(
                        f"Hole spacing too tight between '{tool_a.name}' and '{tool_b.name}'."
                    )

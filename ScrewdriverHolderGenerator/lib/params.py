import math
from dataclasses import dataclass
from typing import Dict, Tuple

import adsk.core
import adsk.fusion


@dataclass
class ParamValues:
    numbers_mm: Dict[str, float]
    strings: Dict[str, str]
    angles_deg: Dict[str, float]


PARAM_DEFS: Tuple[Tuple[str, str, str, str], ...] = (
    ("handle_x_pad", "6 mm", "Extra X spacing per column beyond handle diameter", "length"),
    ("handle_y_pad", "6 mm", "Extra Y spacing per row beyond handle diameter", "length"),
    ("edge_margin_x", "10 mm", "Left/right margin from outermost tools", "length"),
    ("edge_margin_y", "10 mm", "Front/back margin from outermost tools", "length"),
    ("min_web", "3 mm", "Minimum web thickness between holes", "length"),
    ("row_z_step", "8 mm", "Row height step", "length"),
    ("base_thickness", "12 mm", "Base thickness", "length"),
    ("min_floor_thickness", "8 mm", "Minimum platform thickness", "length"),
    ("hole_buffer", "0.6 mm", "Hole clearance buffer", "length"),
    ("hole_chamfer_d", "2.0 mm", "Hole chamfer top width", "length"),
    ("hole_chamfer_depth", "1.5 mm", "Hole chamfer depth", "length"),
    ("text_y_dist", "4 mm", "Distance in front of hole center", "length"),
    ("text_height", "5 mm", "Sketch text height", "length"),
    ("emboss_height", "0.8 mm", "Emboss extrusion height", "length"),
    ("font_name", "Arial", "Font name for labels", "string"),
    ("mount_hole_d", "5.2 mm", "Mounting hole diameter", "length"),
    ("mount_hole_edge_offset_x", "12 mm", "Mount hole offset from left/right edges", "length"),
    ("mount_hole_edge_offset_y", "12 mm", "Mount hole offset from front/back edges", "length"),
    ("mount_style", "counterbore", "Mount style (none, countersink, counterbore)", "string"),
    ("cbore_d", "9.5 mm", "Counterbore diameter", "length"),
    ("cbore_depth", "3.0 mm", "Counterbore depth", "length"),
    ("csk_d", "10 mm", "Countersink diameter", "length"),
    ("csk_angle", "90 deg", "Countersink included angle", "angle"),
)


def ensure_user_parameters(design: adsk.fusion.Design) -> ParamValues:
    user_params = design.userParameters

    for name, expression, comment, kind in PARAM_DEFS:
        if user_params.itemByName(name):
            continue
        value_input = adsk.core.ValueInput.createByString(expression)
        unit = ""
        if kind == "length":
            unit = "mm"
        elif kind == "angle":
            unit = "deg"
        user_params.add(name, value_input, unit, comment)

    numbers_mm: Dict[str, float] = {}
    strings: Dict[str, str] = {}
    angles_deg: Dict[str, float] = {}

    for name, _expression, _comment, kind in PARAM_DEFS:
        param = user_params.itemByName(name)
        if param is None:
            continue
        if kind == "length":
            numbers_mm[name] = param.value * 10.0
        elif kind == "angle":
            angles_deg[name] = math.degrees(param.value)
        else:
            strings[name] = param.expression.strip('"')

    return ParamValues(numbers_mm=numbers_mm, strings=strings, angles_deg=angles_deg)

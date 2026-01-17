import math
from typing import Dict, List, Tuple

import adsk.core
import adsk.fusion

from .csv_reader import Tool
from .layout import Layout


def _mm_to_cm(value_mm: float) -> float:
    return value_mm / 10.0


def _point(x_mm: float, y_mm: float, z_mm: float = 0.0) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(_mm_to_cm(x_mm), _mm_to_cm(y_mm), _mm_to_cm(z_mm))


def _build_base(comp: adsk.fusion.Component, layout: Layout, params: Dict[str, float]) -> adsk.fusion.ExtrudeFeature:
    base_thickness_mm = params["base_thickness"]
    edge_margin_y = params["edge_margin_y"]

    # Base covers all rows but not the back margin
    # This prevents the base from sticking out behind the top tier
    base_depth = edge_margin_y + sum(layout.row_depths[i] for i in range(layout.max_row + 1))

    sketches = comp.sketches
    sketch = sketches.add(comp.xYConstructionPlane)
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        _point(0, 0),
        _point(layout.part_width_mm, base_depth),
    )
    profile = sketch.profiles.item(0)
    extrudes = comp.features.extrudeFeatures
    distance = adsk.core.ValueInput.createByReal(_mm_to_cm(base_thickness_mm))
    extrude = extrudes.addSimple(profile, distance, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    return extrude


def _build_steps(
    comp: adsk.fusion.Component,
    layout: Layout,
    params: Dict[str, float],
) -> None:
    row_z_step = params["row_z_step"]
    base_thickness = params["base_thickness"]
    if layout.max_row < 1:
        return

    planes = comp.constructionPlanes
    sketches = comp.sketches
    extrudes = comp.features.extrudeFeatures

    for row in range(1, layout.max_row + 1):
        z_offset = base_thickness + (row - 1) * row_z_step
        plane_input = planes.createInput()
        plane_input.setByOffset(comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(_mm_to_cm(z_offset)))
        plane = planes.add(plane_input)

        row_start = params["edge_margin_y"] + sum(layout.row_depths[i] for i in range(row))
        row_end = layout.part_depth_mm - params["edge_margin_y"]  # Extend to back edge

        sketch = sketches.add(plane)
        sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            _point(0, row_start),
            _point(layout.part_width_mm, row_end),
        )
        profile = sketch.profiles.item(0)
        distance = adsk.core.ValueInput.createByReal(_mm_to_cm(row_z_step))
        extrudes.addSimple(profile, distance, adsk.fusion.FeatureOperations.JoinFeatureOperation)


def _cut_through_all(comp: adsk.fusion.Component, profile: adsk.fusion.Profile) -> None:
    extrudes = comp.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extent = adsk.fusion.ThroughAllExtentDefinition.create()
    extrude_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    extrudes.add(extrude_input)


def _create_tool_holes(
    comp: adsk.fusion.Component,
    tools: List[Tool],
    layout: Layout,
    params: Dict[str, float],
) -> None:
    sketch = comp.sketches.add(comp.xYConstructionPlane)
    circles = sketch.sketchCurves.sketchCircles

    for tool in tools:
        center = layout.centers[(tool.row, tool.col)]
        hole_d = tool.shaft_d_mm + params["hole_buffer"]
        circles.addByCenterRadius(_point(center[0], center[1]), _mm_to_cm(hole_d / 2))

    for profile in sketch.profiles:
        _cut_through_all(comp, profile)


def _collect_hole_edges(
    body: adsk.fusion.BRepBody,
    centers: Dict[Tuple[int, int], Tuple[float, float]],
    row_zs: Dict[int, float],
) -> Dict[Tuple[int, int], adsk.fusion.BRepEdge]:
    edges: Dict[Tuple[int, int], adsk.fusion.BRepEdge] = {}
    tol = 1e-4
    for edge in body.edges:
        geom = edge.geometry
        if not isinstance(geom, adsk.core.Circle3D):
            continue
        center_cm = geom.center
        for key, (x_mm, y_mm) in centers.items():
            z_mm = row_zs[key[0]]
            if (
                abs(center_cm.x - _mm_to_cm(x_mm)) < tol
                and abs(center_cm.y - _mm_to_cm(y_mm)) < tol
                and abs(center_cm.z - _mm_to_cm(z_mm)) < tol
            ):
                edges[key] = edge
                break
    return edges


def _chamfer_holes(
    comp: adsk.fusion.Component,
    tools: List[Tool],
    layout: Layout,
    params: Dict[str, float],
) -> List[str]:
    warnings: List[str] = []
    body = comp.bRepBodies.item(0)
    row_zs = {
        row: params["base_thickness"] + row * params["row_z_step"] for row in range(layout.max_row + 1)
    }
    edge_map = _collect_hole_edges(body, layout.centers, row_zs)

    chamfer_features = comp.features.chamferFeatures
    for tool in tools:
        key = (tool.row, tool.col)
        edge = edge_map.get(key)
        if edge is None:
            warnings.append(f"Could not find chamfer edge for {tool.name}.")
            continue
        edge_collection = adsk.core.ObjectCollection.create()
        edge_collection.add(edge)
        chamfer_input = chamfer_features.createInput(edge_collection, True)
        depth = _mm_to_cm(params["hole_chamfer_depth"])
        width = _mm_to_cm(params["hole_chamfer_d"] / 2)
        chamfer_input.setToTwoDistances(adsk.core.ValueInput.createByReal(depth), adsk.core.ValueInput.createByReal(width))
        chamfer_features.add(chamfer_input)

    return warnings


def _add_text_labels(
    comp: adsk.fusion.Component,
    tools: List[Tool],
    layout: Layout,
    params: Dict[str, float],
    font_name: str,
) -> List[str]:
    warnings: List[str] = []
    sketches = comp.sketches
    extrudes = comp.features.extrudeFeatures

    tools_by_row: Dict[int, List[Tool]] = {}
    for tool in tools:
        tools_by_row.setdefault(tool.row, []).append(tool)

    for row, row_tools in tools_by_row.items():
        z_offset = params["base_thickness"] + row * params["row_z_step"]
        plane_input = comp.constructionPlanes.createInput()
        plane_input.setByOffset(comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(_mm_to_cm(z_offset)))
        plane = comp.constructionPlanes.add(plane_input)

        sketch = sketches.add(plane)
        sketch_texts = sketch.sketchTexts
        height = _mm_to_cm(params["text_height"])

        row_start = params["edge_margin_y"] + sum(layout.row_depths[i] for i in range(row))
        row_end = row_start + layout.row_depths[row]

        for tool in row_tools:
            x_center, y_center = layout.centers[(tool.row, tool.col)]
            y_text = y_center - (tool.handle_d_mm / 2 + params["text_y_dist"])
            if y_text < row_start + params["min_web"]:
                y_text = row_start + params["min_web"]
                warnings.append(f"Text for {tool.name} clamped to row boundary.")
            if y_text > row_end - params["min_web"]:
                y_text = row_end - params["min_web"]
                warnings.append(f"Text for {tool.name} clamped to row boundary.")

            text_input = sketch_texts.createInput(tool.name, height, _point(x_center, y_text))
            text_input.fontName = font_name
            text_input.horizontalAlignment = adsk.core.HorizontalAlignments.CenterHorizontalAlignment
            text_input.verticalAlignment = adsk.core.VerticalAlignments.MiddleVerticalAlignment
            sketch_texts.add(text_input)

        for profile in sketch.profiles:
            distance = adsk.core.ValueInput.createByReal(_mm_to_cm(params["emboss_height"]))
            extrudes.addSimple(profile, distance, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    return warnings


def _create_mount_holes(
    comp: adsk.fusion.Component,
    layout: Layout,
    params: Dict[str, float],
    mount_style: str,
    csk_angle_deg: float,
) -> None:
    """Create mounting plate at back of holder with 4 screw holes.

    The mounting plate:
    - Spans full width plus wing extensions on both sides
    - Located at the back (+Y end) of the holder
    - Extends upward (+Z) above the top tier
    - Has 4 holes: 2 at bottom corners of extensions, 2 at top corners
    """
    hole_d = params["mount_hole_d"]
    wing_extension = params["mount_hole_edge_offset_x"]  # How far plate extends beyond holder in ±X
    wing_thickness = params["mount_hole_edge_offset_y"]  # Plate thickness in Y
    base_thickness = params["base_thickness"]
    row_z_step = params["row_z_step"]
    edge_margin_y = params["edge_margin_y"]

    # Calculate base_depth (where the holder body ends in Y)
    base_depth = edge_margin_y + sum(layout.row_depths[i] for i in range(layout.max_row + 1))

    # Calculate wing dimensions
    top_tier_z = base_thickness + layout.max_row * row_z_step
    wing_z_height = top_tier_z + base_thickness  # Total height to accommodate holder + upper holes

    # Create one continuous mounting plate at back of holder
    # Sketch on XZ plane offset to Y = base_depth (back of holder body)
    planes = comp.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(
        comp.xZConstructionPlane,
        adsk.core.ValueInput.createByReal(_mm_to_cm(base_depth))
    )
    back_plane = planes.add(plane_input)

    sketch_wing = comp.sketches.add(back_plane)
    lines = sketch_wing.sketchCurves.sketchLines

    # One rectangle spanning full width plus extensions
    # Shifted by wing_z_height in +Z direction (negative in sketch Y means positive world Z)
    lines.addTwoPointRectangle(
        adsk.core.Point3D.create(_mm_to_cm(-wing_extension), _mm_to_cm(-wing_z_height), 0),
        adsk.core.Point3D.create(_mm_to_cm(layout.part_width_mm + wing_extension), 0, 0)
    )

    # Extrude plate in +Y direction (toward wall)
    extrudes = comp.features.extrudeFeatures
    profile = sketch_wing.profiles.item(0)
    distance = adsk.core.ValueInput.createByReal(_mm_to_cm(wing_thickness))
    extrudes.addSimple(profile, distance, adsk.fusion.FeatureOperations.JoinFeatureOperation)

    # 4 hole positions: bottom-left, bottom-right, top-left, top-right
    # Holes are in the extension areas (beyond the holder body)
    # In sketch coords: Y is negative (maps to +Z in world)
    hole_x_left = -wing_extension / 2
    hole_x_right = layout.part_width_mm + wing_extension / 2
    hole_z_bottom = -(base_thickness / 2)  # Near sketch Y=0 (top of wing in world Z)
    hole_z_top = -(wing_z_height - base_thickness / 2)  # Near sketch Y=-wing_z_height (bottom in world Z)

    hole_positions = [
        (hole_x_left, hole_z_bottom),   # Bottom left
        (hole_x_right, hole_z_bottom),  # Bottom right
        (hole_x_left, hole_z_top),      # Top left
        (hole_x_right, hole_z_top),     # Top right
    ]

    # Create holes through plate in Y direction
    # Sketch on the back face of plate (Y = base_depth + wing_thickness)
    plane_input2 = planes.createInput()
    plane_input2.setByOffset(
        comp.xZConstructionPlane,
        adsk.core.ValueInput.createByReal(_mm_to_cm(base_depth + wing_thickness))
    )
    wing_back_plane = planes.add(plane_input2)

    sketch_holes = comp.sketches.add(wing_back_plane)
    for x_mm, z_mm in hole_positions:
        sketch_holes.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(_mm_to_cm(x_mm), _mm_to_cm(z_mm), 0),
            _mm_to_cm(hole_d / 2)
        )

    # Cut through all in -Y direction (through plate)
    for profile in sketch_holes.profiles:
        extrude_input = extrudes.createInput(profile, adsk.fusion.FeatureOperations.CutFeatureOperation)
        extent = adsk.fusion.ThroughAllExtentDefinition.create()
        extrude_input.setOneSideExtent(extent, adsk.fusion.ExtentDirections.NegativeExtentDirection)
        extrudes.add(extrude_input)

    mount_style = mount_style.lower()
    if mount_style == "none":
        return

    # Counterbore on back face of plate (where screw head sits against wall)
    if mount_style == "counterbore":
        cbore_d = params["cbore_d"]
        cbore_depth = params["cbore_depth"]
        sketch_cbore = comp.sketches.add(wing_back_plane)
        for x_mm, z_mm in hole_positions:
            sketch_cbore.sketchCurves.sketchCircles.addByCenterRadius(
                adsk.core.Point3D.create(_mm_to_cm(x_mm), _mm_to_cm(z_mm), 0),
                _mm_to_cm(cbore_d / 2)
            )
        for prof in sketch_cbore.profiles:
            dist = adsk.core.ValueInput.createByReal(_mm_to_cm(cbore_depth))
            extrude_input = extrudes.createInput(prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
            extrude_input.setOneSideExtent(
                adsk.fusion.DistanceExtentDefinition.create(dist),
                adsk.fusion.ExtentDirections.NegativeExtentDirection
            )
            extrudes.add(extrude_input)

    if mount_style == "countersink":
        csk_d = params["csk_d"]
        chamfer_features = comp.features.chamferFeatures
        body = comp.bRepBodies.item(0)
        tol = 1e-4
        back_y = _mm_to_cm(base_depth + wing_thickness)
        distance_val = _mm_to_cm((csk_d - hole_d) / 2)
        angle = math.radians(csk_angle_deg / 2)
        # Find hole edges on back face of plate
        for edge in body.edges:
            geom = edge.geometry
            if not isinstance(geom, adsk.core.Circle3D):
                continue
            if abs(geom.center.y - back_y) > tol:
                continue
            if abs(geom.radius - _mm_to_cm(hole_d / 2)) > tol:
                continue
            edge_collection = adsk.core.ObjectCollection.create()
            edge_collection.add(edge)
            chamfer_input = chamfer_features.createInput(edge_collection, True)
            chamfer_input.setToDistanceAndAngle(
                adsk.core.ValueInput.createByReal(distance_val),
                adsk.core.ValueInput.createByReal(angle),
            )
            chamfer_features.add(chamfer_input)


def build_holder(
    design: adsk.fusion.Design,
    tools: List[Tool],
    layout: Layout,
    params: Dict[str, float],
    strings: Dict[str, str],
    angles: Dict[str, float],
) -> List[str]:
    root = design.rootComponent

    # Check if this is a single-component Part document
    # Parts cannot have sub-components; need to work on root directly
    is_single_component_doc = len(root.occurrences) == 0 and len(root.bRepBodies) == 0

    if is_single_component_doc:
        # Work directly on the root component for Part documents
        # Note: root component name cannot be changed in Fusion 360
        comp = root
    else:
        # Assembly document: use sub-component pattern for clean regeneration
        for occ in list(root.occurrences):
            if occ.component.name == "ScrewdriverHolder_GEN":
                occ.deleteMe()
        occurrence = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occurrence.component
        comp.name = "ScrewdriverHolder_GEN"

    _build_base(comp, layout, params)
    _build_steps(comp, layout, params)
    _create_tool_holes(comp, tools, layout, params)
    warnings = _chamfer_holes(comp, tools, layout, params)

    text_warnings = _add_text_labels(
        comp,
        tools,
        layout,
        params,
        strings.get("font_name", "Arial"),
    )
    warnings.extend(text_warnings)

    _create_mount_holes(
        comp,
        layout,
        params,
        strings.get("mount_style", "counterbore"),
        angles.get("csk_angle", 90.0),
    )

    return warnings

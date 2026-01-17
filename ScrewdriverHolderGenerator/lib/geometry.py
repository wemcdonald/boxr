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


def _build_base(comp: adsk.fusion.Component, layout: Layout, base_thickness_mm: float) -> adsk.fusion.ExtrudeFeature:
    sketches = comp.sketches
    sketch = sketches.add(comp.xYConstructionPlane)
    rect = sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        _point(0, 0),
        _point(layout.part_width_mm, layout.part_depth_mm),
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
    hole_d = params["mount_hole_d"]
    offset_x = params["mount_hole_edge_offset_x"]
    offset_y = params["mount_hole_edge_offset_y"]

    points = [
        (offset_x, offset_y),
        (layout.part_width_mm - offset_x, offset_y),
        (offset_x, layout.part_depth_mm - offset_y),
        (layout.part_width_mm - offset_x, layout.part_depth_mm - offset_y),
    ]

    sketch = comp.sketches.add(comp.xYConstructionPlane)
    circles = sketch.sketchCurves.sketchCircles
    for x_mm, y_mm in points:
        circles.addByCenterRadius(_point(x_mm, y_mm), _mm_to_cm(hole_d / 2))

    for profile in sketch.profiles:
        _cut_through_all(comp, profile)

    mount_style = mount_style.lower()
    if mount_style == "none":
        return

    if mount_style == "counterbore":
        cbore_d = params["cbore_d"]
        cbore_depth = params["cbore_depth"]
        sketch_cbore = comp.sketches.add(comp.xYConstructionPlane)
        for x_mm, y_mm in points:
            sketch_cbore.sketchCurves.sketchCircles.addByCenterRadius(
                _point(x_mm, y_mm), _mm_to_cm(cbore_d / 2)
            )
        for profile in sketch_cbore.profiles:
            extrudes = comp.features.extrudeFeatures
            distance = adsk.core.ValueInput.createByReal(_mm_to_cm(cbore_depth))
            extrude = extrudes.addSimple(profile, distance, adsk.fusion.FeatureOperations.CutFeatureOperation)
            _ = extrude
        return

    if mount_style == "countersink":
        chamfer_features = comp.features.chamferFeatures
        body = comp.bRepBodies.item(0)
        tol = 1e-4
        distance = _mm_to_cm((params["csk_d"] - hole_d) / 2)
        angle = math.radians(csk_angle_deg / 2)
        for edge in body.edges:
            geom = edge.geometry
            if not isinstance(geom, adsk.core.Circle3D):
                continue
            if abs(geom.center.z) > tol:
                continue
            if abs(geom.radius - _mm_to_cm(hole_d / 2)) > tol:
                continue
            edge_collection = adsk.core.ObjectCollection.create()
            edge_collection.add(edge)
            chamfer_input = chamfer_features.createInput(edge_collection, True)
            chamfer_input.setToDistanceAndAngle(
                adsk.core.ValueInput.createByReal(distance),
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

    _build_base(comp, layout, params["base_thickness"])
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

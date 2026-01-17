# Screwdriver Holder Generator - Developer Guide

## Overview

This document provides technical details for developers who want to understand, modify, or extend the Screwdriver Holder Generator Fusion 360 add-in.

## Architecture

### Project Structure

```
ScrewdriverHolderGenerator/
├── ScrewdriverHolderGenerator.manifest    # Add-in metadata
├── ScrewdriverHolderGenerator.py          # Main entry point & Fusion command wiring
├── __init__.py                             # Package marker
├── lib/
│   ├── __init__.py                         # Library package marker
│   ├── csv_reader.py                       # CSV parsing & Tool data structure
│   ├── validate.py                         # Input validation functions
│   ├── params.py                           # User parameter management
│   ├── layout.py                           # Layout computation algorithm
│   └── geometry.py                         # 3D geometry construction
├── USER_GUIDE.md                           # End-user documentation
└── DEVELOPER_GUIDE.md                      # This file
```

### Module Responsibilities

| Module | Purpose | Key Functions/Classes |
|--------|---------|----------------------|
| `ScrewdriverHolderGenerator.py` | Fusion 360 command registration and event handling | `run()`, `stop()`, `GenerateCommandExecuteHandler` |
| `csv_reader.py` | Parse CSV files into Tool objects | `read_tools_from_csv()`, `Tool` dataclass |
| `validate.py` | Validate inputs and constraints | `validate_tools()`, `validate_spacing()`, `validate_mount_offsets()` |
| `params.py` | Create and read Fusion user parameters | `ensure_user_parameters()`, `ParamValues` dataclass |
| `layout.py` | Compute tool positions and part dimensions | `compute_layout()`, `Layout` dataclass |
| `geometry.py` | Build 3D geometry in Fusion 360 | `build_holder()`, `_build_base()`, `_create_tool_holes()`, etc. |

## Data Flow

```
CSV File
   ↓
csv_reader.py → List[Tool]
   ↓
validate.py → validate_tools()
   ↓
params.py → ParamValues (from Fusion user parameters)
   ↓
layout.py → Layout (computed positions & dimensions)
   ↓
validate.py → validate_spacing(), validate_mount_offsets()
   ↓
geometry.py → build_holder() → Fusion 360 Component
   ↓
Result summary + warnings
```

## Data Structures

### Tool (csv_reader.py)

Represents a single tool from the CSV.

```python
@dataclass
class Tool:
    name: str              # Display label
    row: int              # Row index (0 = front)
    col: int              # Column index (0 = left)
    handle_d_mm: float    # Handle diameter in mm
    shaft_d_mm: float     # Shaft diameter in mm
    enabled: bool = True  # Whether tool is active
```

### ParamValues (params.py)

Holds all user-defined parameters from Fusion 360.

```python
@dataclass
class ParamValues:
    numbers_mm: Dict[str, float]    # Length parameters in mm
    strings: Dict[str, str]         # String parameters (font, mount style)
    angles_deg: Dict[str, float]    # Angle parameters in degrees
```

**Note**: Fusion 360 internally uses centimeters, so conversion is handled in `params.py` (multiply by 10 for mm) and `geometry.py` (divide by 10 for cm).

### Layout (layout.py)

Computed layout information for the holder.

```python
@dataclass
class Layout:
    col_widths: Dict[int, float]                      # Width of each column in mm
    row_depths: Dict[int, float]                      # Depth of each row in mm
    centers: Dict[Tuple[int, int], Tuple[float, float]]  # (row,col) → (x_mm, y_mm)
    part_width_mm: float                              # Total part width
    part_depth_mm: float                              # Total part depth
    max_row: int                                      # Highest row index
    max_col: int                                      # Highest column index
```

## Core Algorithms

### Layout Computation (layout.py)

The layout algorithm determines tool spacing and positions:

1. **Compute max handle diameter per column/row**:
   - For each column: `col_max[c] = max(handle_d for tools in column c)`
   - For each row: `row_max[r] = max(handle_d for tools in row r)`

2. **Compute column widths and row depths**:
   ```python
   col_width[c] = max(col_max[c] + handle_x_pad, col_max[c] + min_web)
   row_depth[r] = max(row_max[r] + handle_y_pad, row_max[r] + min_web)
   ```

3. **Fill missing columns/rows**:
   - If columns 0, 2, 3 exist but not 1, create column 1 with width = `min_web`
   - Same for rows

4. **Compute tool centers**:
   ```python
   x_center = edge_margin_x + sum(col_widths[0..c-1]) + col_width[c] / 2
   y_center = edge_margin_y + sum(row_depths[0..r-1]) + row_depth[r] / 2
   ```

5. **Compute part dimensions**:
   ```python
   part_width = 2 * edge_margin_x + sum(all col_widths)
   part_depth = 2 * edge_margin_y + sum(all row_depths) + mounting_wing_depth
   ```

   The `mounting_wing_depth` extends the part past the back row to provide a flat area for wall mounting holes, ensuring they don't interfere with tool holes.

### Validation (validate.py)

**validate_tools()**:
- Ensures at least one tool exists
- Checks for non-empty names
- Validates row/col >= 0
- Validates diameters > 0
- Checks for duplicate (row, col) positions

**validate_spacing()**:
- For tools in the same row: checks horizontal spacing
- For tools in the same column: checks vertical spacing
- Minimum spacing = `(shaft_d_a + shaft_d_b) / 2 + min_web`

**validate_mount_offsets()**:
- Ensures mounting holes don't overlap part edges
- Checks: `offset >= hole_radius + min_web`
- Checks: `offset < part_dimension - hole_radius - min_web`

**validate_params()**:
- Ensures `base_thickness >= min_floor_thickness`

### Geometry Construction (geometry.py)

The geometry is built in this order:

#### 1. Component Management

The add-in handles both Part and Assembly design modes:

**Part Mode** (single component only):
```python
# Part designs can only have the root component
# Work directly in root, clean up previous bodies
for body in list(root.bRepBodies):
    if body.name.startswith("ScrewdriverHolder_GEN"):
        body.deleteMe()

comp = root
# After building geometry, name the body for future cleanup
comp.bRepBodies.item(0).name = "ScrewdriverHolder_GEN"
```

**Assembly Mode** (multiple components allowed):
```python
# Delete old component occurrence if it exists
for occ in root.occurrences:
    if occ.component.name == "ScrewdriverHolder_GEN":
        occ.deleteMe()

# Create new component occurrence
occurrence = root.occurrences.addNewComponent(Matrix3D.create())
comp = occurrence.component
comp.name = "ScrewdriverHolder_GEN"
```

**Detection Logic**:
```python
design_type = design.designType
is_part_design = (design_type == DesignTypes.DirectDesignType or
                  design_type == DesignTypes.ParametricDesignType)
can_create_occurrence = len(list(root.occurrences)) > 0 or not is_part_design
```

This ensures the add-in works seamlessly regardless of design mode.

#### 2. Base Slab (`_build_base`)
- Sketch rectangle on XY plane (0,0) to (W, D)
- Extrude upward by `base_thickness`
- Operation: NewBodyFeatureOperation

#### 3. Stepped Row Platforms (`_build_steps`)
For each row r >= 1:
- Create construction plane at Z = `base_thickness + (r-1) * row_z_step`
- Sketch rectangle spanning:
  - X: [0, part_width]
  - Y: [row_start, part_depth] where row_start is the front edge of this row
- Extrude upward by `row_z_step`
- Operation: JoinFeatureOperation

**Key design**: Each platform extends from the front of its row all the way to the back edge (including the mounting wing). This creates solid stepped platforms rather than floating strips, providing structural integrity and a continuous back surface for wall mounting.

Result: Each row is higher than the previous, with solid platforms extending to the back.

#### 4. Tool Holes (`_create_tool_holes`)
- Create single sketch on XY plane
- Add circle at each (x_center, y_center) with diameter = `shaft_d + hole_buffer`
- Cut through all profiles using ThroughAllExtentDefinition
- Operation: CutFeatureOperation

#### 5. Hole Chamfers (`_chamfer_holes`)
- Traverse body edges to find circular edges at each hole position
- Match edges by:
  - Edge is a Circle3D
  - Center matches (x_center, y_center, z_row)
  - Tolerance: 1e-4 cm
- Apply chamfer to each edge:
  - Distance 1: `hole_chamfer_depth`
  - Distance 2: `hole_chamfer_d / 2`
- Returns warnings if edges can't be found

#### 6. Text Labels (`_add_text_labels`)
For each row:
- Create construction plane at Z = `base_thickness + row * row_z_step`
- Create sketch on that plane
- For each tool in row:
  - Position: `(x_center, y_center - handle_d/2 - text_y_dist)`
  - Add sketch text with:
    - Font: from `font_name` parameter
    - Height: `text_height`
    - Horizontal alignment: Center
    - Vertical alignment: Middle
  - Clamp Y position if it would exceed row boundaries (with warning)
- Extrude all text profiles upward by `emboss_height`
- Operation: JoinFeatureOperation

#### 7. Mounting Holes (`_create_mount_holes`)
- Sketch 4 circles at corner positions:
  - (offset_x, offset_y)
  - (W - offset_x, offset_y)
  - (offset_x, D - offset_y)
  - (W - offset_x, D - offset_y)
- Cut through all
- If `mount_style == "counterbore"`:
  - Sketch 4 larger circles at same positions
  - Cut downward by `cbore_depth`
- If `mount_style == "countersink"`:
  - Find hole edges at Z=0 (bottom face)
  - Apply chamfer with:
    - Distance: `(csk_d - mount_hole_d) / 2`
    - Angle: `csk_angle / 2` (half-angle for chamfer API)

## Fusion 360 API Notes

### Units

- **Fusion internal**: Centimeters (cm)
- **User-facing**: Millimeters (mm) for convenience
- **Conversions**:
  ```python
  def _mm_to_cm(value_mm: float) -> float:
      return value_mm / 10.0

  # When reading user parameters with unit="mm":
  param.value  # Returns in cm (Fusion internal)
  param.value * 10.0  # Convert to mm
  ```

### Creating Geometry

**Sketch + Extrude Pattern**:
```python
sketch = component.sketches.add(construction_plane)
# Add sketch entities (lines, circles, text, etc.)
profile = sketch.profiles.item(0)  # or iterate through profiles

extrudes = component.features.extrudeFeatures
distance = adsk.core.ValueInput.createByReal(distance_in_cm)
extrude = extrudes.addSimple(
    profile,
    distance,
    operation  # NewBody, Join, Cut, Intersect
)
```

**Through-All Cuts**:
```python
extrude_input = extrudes.createInput(profile, CutFeatureOperation)
extent = adsk.fusion.ThroughAllExtentDefinition.create()  # No arguments
extrude_input.setOneSideExtent(extent, PositiveExtentDirection)
extrudes.add(extrude_input)
```

**Chamfers**:
```python
edge_collection = adsk.core.ObjectCollection.create()
edge_collection.add(edge)

chamfer_input = chamfer_features.createInput(edge_collection, is_offset_chamfer=True)

# Two distances (asymmetric):
chamfer_input.setToTwoDistances(distance1, distance2)

# Equal distance (symmetric):
chamfer_input.setToEqualDistance(distance)

# Distance + Angle:
chamfer_input.setToDistanceAndAngle(distance, angle_in_radians)

chamfer_features.add(chamfer_input)
```

**Sketch Text**:
```python
text_input = sketch.sketchTexts.createInput(
    text_string,
    height_in_cm,
    position_point
)
text_input.fontName = "Arial"
text_input.horizontalAlignment = CenterHorizontalAlignment
text_input.verticalAlignment = MiddleVerticalAlignment
sketch.sketchTexts.add(text_input)

# Then extrude the resulting profiles
```

### Edge Selection

Finding specific edges (e.g., for chamfers) can be tricky:

```python
for edge in body.edges:
    geom = edge.geometry
    if isinstance(geom, adsk.core.Circle3D):
        # Check position
        if abs(geom.center.x - target_x) < tolerance:
            # This is our edge
```

**Tolerance**: Use 1e-4 cm for position matching.

### User Parameters

```python
# Create parameter:
value_input = adsk.core.ValueInput.createByString("12 mm")
design.userParameters.add(name, value_input, unit="mm", comment="Description")

# Read parameter:
param = design.userParameters.itemByName(name)
value_cm = param.value  # Internal value in cm
expression = param.expression  # e.g., "12 mm"
```

## Extending the Add-in

### Adding New Parameters

1. Add to `PARAM_DEFS` in `params.py`:
   ```python
   ("my_param", "default_value", "Description", "length"|"angle"|"string")
   ```

2. Use in geometry code:
   ```python
   my_value = params["my_param"]  # or strings["my_param"] or angles_deg["my_param"]
   ```

### Adding New Validation

Add validation function to `validate.py`:
```python
def validate_my_constraint(params: Dict[str, float]) -> None:
    if params["foo"] > params["bar"]:
        raise ValueError("Foo must be <= bar.")
```

Call in `ScrewdriverHolderGenerator.py`:
```python
validate_my_constraint(param_values.numbers_mm)
```

### Modifying Geometry

All geometry functions are in `geometry.py` and follow this pattern:
```python
def _my_feature(
    comp: adsk.fusion.Component,
    tools: List[Tool],
    layout: Layout,
    params: Dict[str, float],
) -> List[str]:  # warnings
    # Create sketches, extrude, etc.
    return warnings
```

Call from `build_holder()`:
```python
warnings.extend(_my_feature(comp, tools, layout, params))
```

### Adding New CSV Columns

1. Update `Tool` dataclass in `csv_reader.py`
2. Parse in `read_tools_from_csv()`:
   ```python
   my_field = float(row.get("my_field"))
   ```
3. Add to `required` set if mandatory
4. Use in layout or geometry code

## Testing

### Manual Testing Checklist

**CSV Validation**:
- [ ] Missing required columns → error
- [ ] Duplicate (row, col) → error
- [ ] Invalid numbers (negative, zero) → error
- [ ] enabled=0 skips tool

**Layout**:
- [ ] 2 rows × 3 cols generates correctly
- [ ] Varying handle sizes in same column → max used for spacing
- [ ] Sparse grid (missing positions) → correct widths/depths
- [ ] Computed part dimensions match expectations

**Geometry**:
- [ ] Base slab created at correct size
- [ ] Row platforms step upward correctly
- [ ] Holes are through and correctly sized
- [ ] Chamfers applied to hole top edges
- [ ] Text labels on correct row faces
- [ ] 4 mounting holes at corners
- [ ] Counterbore/countersink applied correctly

**Regeneration**:
- [ ] Running twice deletes old component
- [ ] Changing CSV → updates geometry
- [ ] Changing parameters → updates geometry

**Error Handling**:
- [ ] Tight spacing → error with tool names
- [ ] Invalid mount offsets → error
- [ ] No active tools → error

### Regression Tests

The repository includes a test file `test_api_regression.py` (see git history) that validates the generated geometry. Key checks:

- Total tool hole count matches CSV enabled tools
- Mount holes count = 4
- Component name = "ScrewdriverHolder_GEN"
- Body count and feature counts in expected ranges

## Common Development Tasks

### Debugging

Add debug output in command handler:
```python
ui.messageBox(f"Debug: {variable}")
```

Or use Python debugger with Visual Studio Code (see `.vscode/launch.json`).

### Handling API Changes

Fusion 360 API can change between versions. If geometry generation fails:

1. Check edge/face selection logic (most fragile)
2. Update tolerance values if needed
3. Verify extrude operation types haven't changed
4. Check construction plane creation methods

### Performance Optimization

For large tool counts (50+):
- Minimize sketch count (combine features where possible)
- Reuse construction planes
- Avoid redundant body traversals

Current implementation:
- 1 sketch for all tool holes ✓
- 1 sketch per row for text (necessary for different Z planes)
- 1 sketch per row step (necessary for different Z planes)

### Code Style

- Use type hints for all functions
- Use descriptive variable names (avoid single letters except loop indices)
- Private functions prefixed with `_`
- Docstrings not required for simple functions but encouraged for complex logic
- Keep functions short and focused
- Handle errors at the appropriate level (validate early, fail fast)

## Troubleshooting Development Issues

### "Cannot find edge for chamfer"

**Cause**: Edge matching tolerance too strict or geometry changed.

**Fix**:
- Increase tolerance in `_collect_hole_edges()` (current: 1e-4 cm)
- Verify hole was created successfully before chamfering
- Check Z coordinate calculation for row platforms

### "Text extrusion fails"

**Cause**: Text profiles invalid or font not found.

**Fix**:
- Ensure font name is valid on target system
- Check text isn't empty or zero-height
- Verify construction plane exists at correct Z

### "Failed to create component: Part Experiences can only contain one component"

**Cause**: Attempting to create a new component occurrence in Part mode (only Assembly mode supports multiple components).

**Fix**: This is now handled automatically by the code. The add-in detects design mode:
- Part mode: Works directly in root component, names bodies for cleanup
- Assembly mode: Creates a new component occurrence

If you're developing and encounter this, check the `can_create_occurrence` logic in `build_holder()`.

### "Component not found after creation"

**Cause**: Occurrence vs. Component confusion, or working in the wrong mode.

**Fix**:
- Always use `occurrence.component` not just the occurrence
- Check if component was actually added to root
- Verify the design mode detection is working correctly

### Unit Conversion Errors

**Symptom**: Geometry 10x too large/small.

**Cause**: Mixing mm and cm without conversion.

**Fix**:
- Always use `_mm_to_cm()` before passing to Fusion API
- Always multiply by 10 when reading Fusion parameters with mm units

## Architecture Decisions

### Why separate layout and geometry?

- **Testability**: Layout computation can be tested without Fusion API
- **Clarity**: Separates pure math from API-specific code
- **Reusability**: Layout could be used for 2D preview, documentation, etc.

### Why delete and recreate component?

**Alternatives considered**:
- Update features in place (complex, error-prone with timeline)
- Create new occurrence each time (clutters design)

**Chosen approach**: Delete and recreate ensures clean state and predictable results.

### Why through-holes instead of pockets?

**Rationale**:
- Simpler 3D printing (no support cleanup inside pockets)
- Easier to clean/maintain
- Simpler geometry generation code
- Spec requirement from original PRD

### Why one sketch for all tool holes?

**Performance**: Creating one sketch with multiple circles and cutting all profiles at once is much faster than individual hole features.

**Limitation**: Can't easily have different hole depths per tool. If needed in future, switch to multiple HoleFeature operations.

## API Reference

### Key Fusion 360 API Classes

- `adsk.core.Application`: Main application object
- `adsk.fusion.Design`: Current design document
- `adsk.fusion.Component`: Container for features/bodies
- `adsk.fusion.Occurrence`: Instance of a component
- `adsk.fusion.Sketch`: 2D sketch on a plane
- `adsk.fusion.Profile`: Closed region in sketch (can be extruded)
- `adsk.fusion.ExtrudeFeature`: Extruded geometry
- `adsk.fusion.ChamferFeature`: Chamfered edges
- `adsk.core.Point3D`: 3D point
- `adsk.core.ValueInput`: Input value with units

### Useful Fusion API Patterns

**Get active design**:
```python
app = adsk.core.Application.get()
design = adsk.fusion.Design.cast(app.activeProduct)
```

**File dialog**:
```python
file_dialog = ui.createFileDialog()
file_dialog.title = "Select CSV"
file_dialog.filter = "CSV Files (*.csv)"
if file_dialog.showOpen() == adsk.core.DialogResults.DialogOK:
    filename = file_dialog.filename
```

**Message box**:
```python
ui.messageBox("Message text")
```

**Iterate collections**:
```python
for i in range(collection.count):
    item = collection.item(i)
```

or:
```python
for item in collection:
    # item
```

## Contributing

When modifying this add-in:

1. **Read the PRD**: Ensure changes align with original requirements
2. **Test thoroughly**: Use manual test checklist above
3. **Update documentation**: Keep this guide and USER_GUIDE.md in sync with code
4. **Validate edge cases**: Test sparse grids, large tool counts, extreme parameters
5. **Check compatibility**: Test on both Windows and Mac if possible

## Resources

- [Fusion 360 API Documentation](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-A92A4B10-3781-4925-94C6-47DA85A4F65A)
- [Fusion 360 API Samples](https://github.com/AutodeskFusion360/Fusion360AddinSamples)
- [Fusion 360 Python API Reference](https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-7B5A90C8-E94C-48DA-B16B-430729B734DC)

## Version History

- **1.0.0**: Initial release
  - CSV-driven tool layout
  - Stepped row design
  - Embossed labels
  - Chamfered holes
  - Configurable mounting options
  - Full parameter support

## License

[Specify your license here]

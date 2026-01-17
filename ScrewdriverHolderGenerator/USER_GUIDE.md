# Screwdriver Holder Generator - User Guide

## Overview

The Screwdriver Holder Generator is a Fusion 360 add-in that automatically creates customized, 3D-printable wall-mounted holders for screwdrivers and other tools. Simply provide a CSV file describing your tools, and the add-in generates a complete parametric model optimized for 3D printing.

## Features

- **CSV-driven design**: Define your tool layout in a simple spreadsheet
- **Automatic spacing**: Smart layout algorithm ensures proper clearance between tools
- **Stepped row design**: Each row is elevated for easy tool access
- **Through-holes with chamfers**: Clean hole edges for smooth tool insertion
- **Embossed labels**: Each tool position is labeled for easy organization
- **Wall mounting**: Four mounting holes with optional countersink or counterbore
- **Fully parametric**: Adjust all dimensions through Fusion 360 user parameters
- **Regenerable**: Update your CSV or parameters and regenerate the model instantly

## Installation

1. Download the `ScrewdriverHolderGenerator` folder
2. In Fusion 360, go to **Tools → Add-Ins → Scripts and Add-Ins**
3. Click the **Add-Ins** tab
4. Click the green **+** button next to "My Add-Ins"
5. Navigate to and select the `ScrewdriverHolderGenerator` folder
6. Click **Run** to start the add-in

For automatic startup, check "Run on Startup" after adding the add-in.

## Quick Start

### 1. Prepare Your CSV File

Create a CSV file with the following columns:

| Column | Required | Type | Description |
|--------|----------|------|-------------|
| name | Yes | String | Label text for the tool |
| row | Yes | Integer ≥ 0 | Row index (0 = front row, lowest) |
| col | Yes | Integer ≥ 0 | Column index (0 = leftmost) |
| handle_d_mm | Yes | Float > 0 | Handle diameter in millimeters |
| shaft_d_mm | Yes | Float > 0 | Shaft diameter in millimeters |
| enabled | No | 0 or 1 | Set to 0 to skip this tool |

**Example CSV:**

```csv
name,row,col,handle_d_mm,shaft_d_mm,enabled
T10,0,0,18.0,5.0,1
T15,0,1,18.0,5.5,1
T20,0,2,18.0,6.0,1
PH1,1,0,22.0,6.0,1
PH2,1,1,22.0,6.4,1
PH3,1,2,22.0,7.0,1
Flathead,2,0,24.0,6.5,1
```

This creates a 3×3 grid with three rows:
- Row 0 (front): Three T-handle tools
- Row 1 (middle): Three Phillips drivers
- Row 2 (back): One flathead driver

### 2. Generate the Holder

1. In Fusion 360, create a new design or open an existing one
2. Go to **CREATE** panel in the **SOLID** workspace
3. Click **Generate Holder from CSV** (added by the add-in)
4. Select your CSV file
5. Wait for generation to complete (a few seconds)
6. Review the summary dialog showing:
   - Number of tools
   - Number of rows and columns
   - Part dimensions
   - Any warnings

### 3. Review and Adjust

After generation, the holder geometry is created in your design:
- **Assembly designs**: A new component named `ScrewdriverHolder_GEN` is created
- **Part designs**: The geometry is created directly in the root component with a body named `ScrewdriverHolder_GEN`

You can then:
- **View the model**: Rotate, inspect clearances, check labels
- **Adjust parameters**: See "Adjusting Parameters" section below
- **Export for 3D printing**: Export as STL or 3MF

**Note**: The add-in works in both Part and Assembly design modes. If you prefer to keep the holder as a separate component, start with an Assembly design (File → New Design, then ensure you're in Assembly mode).

## CSV Guidelines

### Row and Column Layout

- **Row 0** is the front (lowest) row
- **Column 0** is the leftmost column
- Rows don't need to be consecutive (you can have row 0 and row 2)
- Columns don't need to be consecutive
- Each (row, col) position must be unique

### Handle and Shaft Diameters

- **handle_d_mm**: Used for spacing calculations. Measure the widest part of the handle
- **shaft_d_mm**: Used for hole sizing. Measure the shaft diameter where it goes through the holder
- The actual hole will be slightly larger (controlled by `hole_buffer` parameter)

### Tips

- Group tools by size: Put similar-sized tools in the same row for efficient spacing
- Leave gaps for expansion: Use non-consecutive columns to reserve space for future tools
- Disable tools temporarily: Set `enabled=0` instead of deleting rows

## Adjusting Parameters

All design parameters can be adjusted after generation:

1. Go to **Modify → Change Parameters**
2. Filter by "User Parameters"
3. Adjust any values
4. Re-run **Generate Holder from CSV** with the same CSV to regenerate

### Layout Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| handle_x_pad | 6 mm | Extra horizontal spacing between columns |
| handle_y_pad | 6 mm | Extra vertical spacing between rows |
| edge_margin_x | 10 mm | Left/right margin from tools to part edge |
| edge_margin_y | 10 mm | Front/back margin from tools to part edge |
| mounting_wing_depth | 20 mm | Depth of back extension for wall mounting holes |
| min_web | 3 mm | Minimum wall thickness between features |
| row_z_step | 8 mm | Height difference between consecutive rows |

### Part Structure

| Parameter | Default | Description |
|-----------|---------|-------------|
| base_thickness | 12 mm | Thickness of the base platform (row 0) |
| min_floor_thickness | 8 mm | Minimum platform thickness (safety check) |

### Hole Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| hole_buffer | 0.6 mm | Added clearance to shaft diameter |
| hole_chamfer_d | 2.0 mm | Chamfer width at hole entrance |
| hole_chamfer_depth | 1.5 mm | Chamfer depth |

**Tip**: Increase `hole_buffer` if tools are too tight, decrease for a snugger fit.

### Label Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| text_y_dist | 4 mm | Distance from hole center to label |
| text_height | 5 mm | Height of label text |
| emboss_height | 0.8 mm | How much labels protrude |
| font_name | Arial | Font family for labels |

### Mounting Holes

| Parameter | Default | Description |
|-----------|---------|-------------|
| mount_hole_d | 5.2 mm | Mounting hole diameter |
| mount_hole_edge_offset_x | 12 mm | Distance from left/right edges |
| mount_hole_edge_offset_y | 12 mm | Distance from front/back edges |
| mount_style | counterbore | Options: none, countersink, counterbore |

**For counterbore** (recessed flat-head screws):
- cbore_d | 9.5 mm | Counterbore diameter
- cbore_depth | 3.0 mm | Counterbore depth

**For countersink** (angled screws):
- csk_d | 10 mm | Countersink top diameter
- csk_angle | 90 deg | Countersink included angle (typically 82° or 90°)

**Note on mounting**: The holder includes a back extension (mounting wing) behind the last row of tools. This flat area provides space for the mounting holes so they don't interfere with the screwdriver holes. The `mounting_wing_depth` parameter (default 20mm) controls how far this extension protrudes past the back row. Increase this value if you need more clearance for your mounting screws or wall anchors.

## Common Scenarios

### Changing Tool Arrangement

1. Edit your CSV file: add, remove, or move tools
2. Save the CSV
3. In Fusion 360, run **Generate Holder from CSV** again
4. Select the same or updated CSV file
5. The old holder is automatically deleted and replaced

### Making the Holder Wider/Narrower

Adjust these parameters:
- `handle_x_pad`: More padding = wider
- `edge_margin_x`: More margin = wider overall
- Update CSV with different column spacing

### Making the Holder Taller/Shorter

Adjust:
- `row_z_step`: Height difference between rows
- `base_thickness`: Base height

### Adding Countersink for Flush Mounting

1. Change `mount_style` to "countersink"
2. Set `csk_angle` to match your screw (typically 82 or 90 degrees)
3. Set `csk_d` to the head diameter of your screw
4. Regenerate

### 3D Printing Tips

**Recommended settings:**
- **Orientation**: Print with the back (flat side with mounting holes) on the build plate
- **Layer height**: 0.2-0.3mm
- **Infill**: 20-30% (sufficient strength for light tools)
- **Supports**: Usually not needed with correct orientation
- **Material**: PLA, PETG, or ABS all work well

**Post-processing:**
- Test-fit tools before mounting
- Clean out holes with a drill bit if needed
- Chamfers should allow smooth tool insertion

## Troubleshooting

### Error: "Duplicate row/col"

**Problem**: Two tools have the same (row, col) position.

**Solution**: Check your CSV and ensure each enabled tool has a unique position.

### Error: "Hole spacing too tight"

**Problem**: Two holes would overlap or leave insufficient wall thickness.

**Solution**:
- Increase `handle_x_pad` or `handle_y_pad`
- Increase `min_web`
- Space tools further apart in your CSV (use non-consecutive columns/rows)
- Reduce shaft diameters if measured incorrectly

### Error: "Mount hole offset places holes outside part"

**Problem**: Mounting holes are positioned beyond the part boundaries.

**Solution**:
- Decrease `mount_hole_edge_offset_x` or `mount_hole_edge_offset_y`
- Make your part larger by adding tools or increasing margins

### Warning: "Could not find chamfer edge"

**Problem**: The add-in couldn't locate the hole edge to chamfer.

**Impact**: One hole won't have a chamfer, but the model is still usable.

**Solution**: Usually a Fusion API quirk. Try regenerating, or manually add a chamfer to that hole.

### Warning: "Text clamped to row boundary"

**Problem**: A label would extend outside its row area.

**Impact**: Text is moved slightly, but still readable.

**Solution**:
- Increase `handle_y_pad` for more space
- Reduce `text_height` or `text_y_dist`

## Limitations

- **Text placement**: Labels are placed on flat surfaces only
- **Hole type**: All holes are through-holes (not pockets)
- **Layout**: Uses grid-based placement (no auto-packing)
- **Export**: No direct STL export; use Fusion 360's export feature

## Advanced Usage

### Multi-Set Holders

Create separate CSV files for different tool sets, then generate multiple holders or combine them in a single design with multiple components.

### Custom Mounting Patterns

After generation, you can manually add additional mounting holes or modify the generated geometry within Fusion 360.

### Parametric Families

Create multiple configurations by:
1. Generating a holder
2. Saving the design with a specific name
3. Adjusting parameters or CSV
4. Generating again in a new design

## Support

For issues, feature requests, or questions:
- Check this guide and the DEVELOPER_GUIDE.md
- Review your CSV format and parameter values
- Verify tool measurements are accurate

## Appendix: Parameter Reference

Complete list of all adjustable parameters with defaults:

```
handle_x_pad = 6 mm
handle_y_pad = 6 mm
edge_margin_x = 10 mm
edge_margin_y = 10 mm
mounting_wing_depth = 20 mm
min_web = 3 mm
row_z_step = 8 mm
base_thickness = 12 mm
min_floor_thickness = 8 mm
hole_buffer = 0.6 mm
hole_chamfer_d = 2.0 mm
hole_chamfer_depth = 1.5 mm
text_y_dist = 4 mm
text_height = 5 mm
emboss_height = 0.8 mm
font_name = "Arial"
mount_hole_d = 5.2 mm
mount_hole_edge_offset_x = 12 mm
mount_hole_edge_offset_y = 12 mm
mount_style = "counterbore"
cbore_d = 9.5 mm
cbore_depth = 3.0 mm
csk_d = 10 mm
csk_angle = 90 deg
```

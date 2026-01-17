# Example CSV Files

This directory contains sample CSV files for testing the Screwdriver Holder Generator add-in.

## Test Files

### 1. `single_tool.csv`
**Purpose**: Minimal test case with just one tool.

**Use for**:
- Quick smoke testing
- Verifying basic functionality
- Debugging geometry generation

**Expected result**: Smallest possible holder (one hole with label and 4 mounting holes)

---

### 2. `basic_test.csv`
**Purpose**: Simple test with 5 tools in 2 rows.

**Layout**:
- Row 0: 3 Torx drivers (T10, T15, T20)
- Row 1: 2 Phillips drivers (PH2, PH3)

**Use for**:
- Initial testing of the add-in
- Verifying row stepping
- Quick iteration during development

**Expected result**: Compact 3×2 holder with visible row step

---

### 3. `realistic_screwdriver_set.csv`
**Purpose**: Full workshop screwdriver set with 24 tools in 4 rows.

**Layout**:
- Row 0: 8 Torx drivers (T6-T30)
- Row 1: 5 Phillips drivers (PH0-PH4)
- Row 2: 5 Flathead drivers (2.5mm-6.5mm)
- Row 3: 6 Hex drivers (1.5mm-5.0mm)

**Use for**:
- Testing realistic use case
- Performance testing with moderate tool count
- Verifying label readability with many tools
- Demonstrating the add-in to others

**Expected result**: Professional-looking holder ~250mm wide, 4 stepped rows

---

### 4. `sparse_grid.csv`
**Purpose**: Non-consecutive rows and columns with gaps.

**Layout**:
- Row 0: Tools at columns 0, 2, 5
- Row 2: Tools at columns 1, 4
- Row 4: Tools at columns 0, 3, 5
- Missing: Rows 1, 3 and columns 1, 3, 4 (in some rows)

**Use for**:
- Testing layout algorithm handling of gaps
- Verifying min_web spacing for empty positions
- Testing future expansion capability (reserved spots)

**Expected result**: Holder with visible spacing where no tools exist, proper min_web thickness between all positions

---

### 5. `varying_sizes.csv`
**Purpose**: Wide range of handle sizes to test column width calculation.

**Layout**: 4 rows × 3 columns with handle diameters from 12mm to 36mm

**Key features**:
- Column 0: Ranges from 14mm to 35mm (should use 35mm for width)
- Column 1: Ranges from 12mm to 24mm (should use 24mm for width)
- Column 2: Ranges from 28mm to 36mm (should use 36mm for width)

**Use for**:
- Verifying max-per-column spacing algorithm
- Testing extreme size variations
- Checking hole clearance with different diameters

**Expected result**: Holder with visibly different column widths, all tools properly spaced

---

### 6. `with_disabled_tools.csv`
**Purpose**: Demonstrates the enabled/disabled feature.

**Layout**: 3 rows of tools with some marked enabled=0

**Disabled tools**:
- T15-OLD (replaced by T15-NEW)
- T25-BROKEN
- PH4-MISSING
- Spare-Slot

**Use for**:
- Testing enabled=0 functionality
- Demonstrating tool replacement workflow
- Verifying duplicate position handling (old T15 vs new T15)
- Planning for future expansion

**Expected result**: Only enabled tools appear; position (0,2) has T15-NEW, not T15-OLD

---

## Testing Workflow

### Quick Test
```
single_tool.csv → basic_test.csv → realistic_screwdriver_set.csv
```

### Comprehensive Test
Test all 6 files in order, verifying:
1. Geometry generates without errors
2. Correct number of holes
3. Labels are readable
4. Row stepping is visible
5. Mounting holes are positioned correctly
6. Part dimensions are reasonable

### Stress Test
1. Start with `realistic_screwdriver_set.csv`
2. Adjust parameters (increase/decrease margins, padding, steps)
3. Regenerate and verify geometry updates correctly

## Creating Your Own Test Files

### Minimal CSV Template
```csv
name,row,col,handle_d_mm,shaft_d_mm,enabled
ToolName,0,0,20.0,6.0,1
```

### Common Handle Diameters
- Precision screwdrivers: 12-18mm
- Standard screwdrivers: 18-26mm
- Large screwdrivers: 26-36mm

### Common Shaft Diameters
- Small: 3-5mm
- Medium: 5-7mm
- Large: 7-9mm

### Tips
- Measure actual tools for best fit
- Add 0.5-1mm clearance via `hole_buffer` parameter
- Group similar-sized tools in same row for efficiency
- Use non-consecutive columns to reserve expansion space
- Use descriptive names for easy identification

## Troubleshooting Test Files

### "Duplicate row/col" Error
Check for multiple enabled tools at the same (row, col) position.

### "Hole spacing too tight" Error
- Increase handle diameters if too small
- Space tools further apart (skip columns/rows)
- Increase `handle_x_pad` or `handle_y_pad` parameters

### Text Overlaps or Unreadable
- Reduce tool count per row
- Increase `handle_y_pad` for more front-to-back space
- Adjust `text_y_dist` or `text_height` parameters

### Part Too Large for 3D Printer
- Split into multiple holders
- Reduce margins and padding
- Use more rows instead of columns (depth vs width)

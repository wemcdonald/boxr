import importlib
import sys
import tempfile
import types
import unittest


class FakeValueInput:
    @staticmethod
    def createByReal(value):
        return value

    @staticmethod
    def createByString(value):
        return value


class FakePoint3D:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    @staticmethod
    def create(x, y, z):
        return FakePoint3D(x, y, z)


class FakeCircle3D:
    def __init__(self, center, radius):
        self.center = center
        self.radius = radius


class FakeObjectCollection(list):
    @staticmethod
    def create():
        return FakeObjectCollection()

    def add(self, obj):
        self.append(obj)


class FakeMatrix3D:
    @staticmethod
    def create():
        return FakeMatrix3D()


class FakeProfiles(list):
    def item(self, index):
        return self[index]


class FakeSketchTextInput:
    def __init__(self, text, height, point):
        self.text = text
        self.height = height
        self.point = point
        self.fontName = None
        self.horizontalAlignment = None
        self.verticalAlignment = None


class FakeSketchTexts:
    def __init__(self, sketch):
        self.sketch = sketch
        self.items = []

    def createInput(self, text, height, point):
        return FakeSketchTextInput(text, height, point)

    def add(self, text_input):
        self.items.append(text_input)
        self.sketch.add_profile()


class FakeSketchLines:
    def __init__(self, sketch):
        self.sketch = sketch

    def addTwoPointRectangle(self, _p1, _p2):
        self.sketch.add_profile()


class FakeSketchCircles:
    def __init__(self, sketch):
        self.sketch = sketch
        self.centers = []

    def addByCenterRadius(self, center, radius):
        self.centers.append((center, radius))
        self.sketch.add_profile()


class FakeSketchCurves:
    def __init__(self, sketch):
        self.sketchLines = FakeSketchLines(sketch)
        self.sketchCircles = FakeSketchCircles(sketch)


class FakeSketch:
    def __init__(self):
        self.profiles = FakeProfiles()
        self.sketchCurves = FakeSketchCurves(self)
        self.sketchTexts = FakeSketchTexts(self)

    def add_profile(self):
        self.profiles.append(object())


class FakeSketches(list):
    def add(self, _plane):
        sketch = FakeSketch()
        self.append(sketch)
        return sketch


class FakeConstructionPlaneInput:
    def setByOffset(self, _plane, _value):
        return None


class FakeConstructionPlanes(list):
    def createInput(self):
        return FakeConstructionPlaneInput()

    def add(self, _input):
        plane = object()
        self.append(plane)
        return plane


class FakeExtrudeInput:
    def __init__(self, profile, operation):
        self.profile = profile
        self.operation = operation
        self.extent = None

    def setOneSideExtent(self, extent, _direction):
        self.extent = extent


class FakeExtrudeFeatures:
    def __init__(self):
        self.add_simple_calls = []
        self.add_calls = []

    def addSimple(self, profile, distance, operation):
        self.add_simple_calls.append((profile, distance, operation))
        return object()

    def createInput(self, profile, operation):
        return FakeExtrudeInput(profile, operation)

    def add(self, input_obj):
        self.add_calls.append(input_obj)
        return object()


class FakeChamferInput:
    def __init__(self, edges, _):
        self.edges = edges

    def setToDistanceDistance(self, _depth, _width):
        return None

    def setToDistanceAndAngle(self, _distance, _angle):
        return None


class FakeChamferFeatures:
    def __init__(self):
        self.add_calls = []

    def createInput(self, edges, is_tangent):
        return FakeChamferInput(edges, is_tangent)

    def add(self, chamfer_input):
        self.add_calls.append(chamfer_input)
        return object()


class FakeFeatures:
    def __init__(self):
        self.extrudeFeatures = FakeExtrudeFeatures()
        self.chamferFeatures = FakeChamferFeatures()


class FakeEdge:
    def __init__(self, geometry):
        self.geometry = geometry


class FakeBRepBody:
    def __init__(self, edges):
        self.edges = edges


class FakeBRepBodies(list):
    def item(self, index):
        return self[index]


class FakeComponent:
    def __init__(self, design):
        self.name = ""
        self.xYConstructionPlane = object()
        self.sketches = FakeSketches()
        self.constructionPlanes = FakeConstructionPlanes()
        self.features = FakeFeatures()
        self.bRepBodies = FakeBRepBodies(
            [FakeBRepBody(_build_tool_edges(design))]
        )


def _build_tool_edges(design):
    edges = []
    for tool in design.tools:
        center = design.layout.centers[(tool.row, tool.col)]
        z_mm = design.params["base_thickness"] + tool.row * design.params["row_z_step"]
        circle = FakeCircle3D(
            FakePoint3D(center[0] / 10.0, center[1] / 10.0, z_mm / 10.0),
            (tool.shaft_d_mm + design.params["hole_buffer"]) / 20.0,
        )
        edges.append(FakeEdge(circle))
    return edges


class FakeOccurrence:
    def __init__(self, component, occurrences):
        self.component = component
        self._occurrences = occurrences

    def deleteMe(self):
        self._occurrences.remove(self)


class FakeOccurrences(list):
    def __init__(self, design):
        super().__init__()
        self.design = design

    def addNewComponent(self, _matrix):
        comp = FakeComponent(self.design)
        occ = FakeOccurrence(comp, self)
        self.append(occ)
        return occ


class FakeRootComponent:
    def __init__(self, design):
        self.occurrences = FakeOccurrences(design)
        self.xYConstructionPlane = object()


class FakeDesign:
    def __init__(self, layout, params, tools):
        self.layout = layout
        self.params = params
        self.tools = tools
        self.rootComponent = FakeRootComponent(self)


def _install_fake_adsk():
    fusion_types = types.SimpleNamespace(
        Component=type("Component", (), {}),
        Design=type("Design", (), {}),
        ExtrudeFeature=type("ExtrudeFeature", (), {}),
        Profile=type("Profile", (), {}),
        BRepBody=type("BRepBody", (), {}),
        BRepEdge=type("BRepEdge", (), {}),
    )
    core = types.SimpleNamespace(
        Point3D=FakePoint3D,
        ValueInput=FakeValueInput,
        ObjectCollection=FakeObjectCollection,
        Matrix3D=FakeMatrix3D,
        Circle3D=FakeCircle3D,
        HorizontalAlignments=types.SimpleNamespace(CenterHorizontalAlignment="center"),
        VerticalAlignments=types.SimpleNamespace(MiddleVerticalAlignment="middle"),
    )
    fusion = types.SimpleNamespace(
        FeatureOperations=types.SimpleNamespace(
            NewBodyFeatureOperation="new",
            JoinFeatureOperation="join",
            CutFeatureOperation="cut",
        ),
        ThroughAllExtentDefinition=types.SimpleNamespace(
            create=lambda direction: ("through_all", direction)
        ),
        ExtentDirections=types.SimpleNamespace(PositiveExtentDirection="positive"),
    )
    fusion.__dict__.update(fusion_types.__dict__)
    adsk = types.SimpleNamespace(core=core, fusion=fusion)
    sys.modules["adsk"] = adsk
    sys.modules["adsk.core"] = core
    sys.modules["adsk.fusion"] = fusion


class ApiCallTest(unittest.TestCase):
    def setUp(self):
        _install_fake_adsk()

    def test_api_calls_for_csv(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as csv_file:
            csv_file.write(
                "name,row,col,handle_d_mm,shaft_d_mm,enabled\n"
                "T10,0,0,18.0,5.0,1\n"
                "PH2,1,0,22.0,6.4,1\n"
            )
            csv_path = csv_file.name

        sys.path.insert(0, "/workspace/boxr")
        csv_reader = importlib.import_module(
            "ScrewdriverHolderGenerator.lib.csv_reader"
        )
        layout_mod = importlib.import_module("ScrewdriverHolderGenerator.lib.layout")
        geometry = importlib.import_module("ScrewdriverHolderGenerator.lib.geometry")

        tools = csv_reader.read_tools_from_csv(csv_path)
        params = {
            "handle_x_pad": 6.0,
            "handle_y_pad": 6.0,
            "edge_margin_x": 10.0,
            "edge_margin_y": 10.0,
            "min_web": 3.0,
            "row_z_step": 8.0,
            "base_thickness": 12.0,
            "min_floor_thickness": 8.0,
            "hole_buffer": 0.6,
            "hole_chamfer_d": 2.0,
            "hole_chamfer_depth": 1.5,
            "text_y_dist": 4.0,
            "text_height": 5.0,
            "emboss_height": 0.8,
            "mount_hole_d": 5.2,
            "mount_hole_edge_offset_x": 12.0,
            "mount_hole_edge_offset_y": 12.0,
            "cbore_d": 9.5,
            "cbore_depth": 3.0,
            "csk_d": 10.0,
        }
        layout = layout_mod.compute_layout(tools, params)
        design = FakeDesign(layout, params, tools)

        geometry.build_holder(
            design,
            tools,
            layout,
            params,
            {"font_name": "Arial", "mount_style": "none"},
            {"csk_angle": 90.0},
        )

        comp = design.rootComponent.occurrences[0].component
        extrudes = comp.features.extrudeFeatures
        chamfers = comp.features.chamferFeatures

        self.assertEqual(len(extrudes.add_simple_calls), 4)
        self.assertEqual(len(extrudes.add_calls), 6)
        self.assertEqual(len(chamfers.add_calls), 2)

        text_count = sum(len(sketch.sketchTexts.items) for sketch in comp.sketches)
        self.assertEqual(text_count, 2)


if __name__ == "__main__":
    unittest.main()

import adsk.core
import adsk.fusion
import traceback

from .lib.csv_reader import read_tools_from_csv
from .lib.geometry import build_holder
from .lib.layout import compute_layout
from .lib.params import ensure_user_parameters
from .lib.validate import (
    validate_mount_offsets,
    validate_params,
    validate_spacing,
    validate_tools,
)

CMD_ID = "screwdriver_holder_generate"
CMD_NAME = "Generate Holder from CSV"
CMD_DESC = "Generate a wall-mounted screwdriver holder from a CSV file."
PANEL_ID = "SolidCreatePanel"
WORKSPACE_ID = "FusionSolidEnvironment"

handlers = []


def _show_message(ui: adsk.core.UserInterface, message: str) -> None:
    ui.messageBox(message)


class GenerateCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CommandEventArgs) -> None:
        ui = None
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design:
                _show_message(ui, "No active Fusion design.")
                return

            file_dialog = ui.createFileDialog()
            file_dialog.title = "Select CSV for Screwdriver Holder"
            file_dialog.filter = "CSV Files (*.csv)"
            if file_dialog.showOpen() != adsk.core.DialogResults.DialogOK:
                return

            tools = read_tools_from_csv(file_dialog.filename)
            validate_tools(tools)

            param_values = ensure_user_parameters(design)
            validate_params(param_values.numbers_mm)
            layout = compute_layout(tools, param_values.numbers_mm)

            validate_spacing(tools, layout.centers, param_values.numbers_mm)
            validate_mount_offsets(
                param_values.numbers_mm, layout.part_width_mm, layout.part_depth_mm
            )

            warnings = build_holder(
                design,
                tools,
                layout,
                param_values.numbers_mm,
                param_values.strings,
                param_values.angles_deg,
            )

            summary = (
                f"Generated holder with {len(tools)} tools.\n"
                f"Rows: {layout.max_row + 1}, Columns: {layout.max_col + 1}\n"
                f"Part size: {layout.part_width_mm:.1f} mm x {layout.part_depth_mm:.1f} mm"
            )
            if warnings:
                summary += "\n\nWarnings:\n" + "\n".join(warnings)

            _show_message(ui, summary)
        except Exception:
            if ui:
                _show_message(ui, f"Failed:\n{traceback.format_exc()}")


class GenerateCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args: adsk.core.CommandCreatedEventArgs) -> None:
        cmd = args.command
        on_execute = GenerateCommandExecuteHandler()
        cmd.execute.add(on_execute)
        handlers.append(on_execute)


def run(_context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        command_def = ui.commandDefinitions.itemById(CMD_ID)
        if not command_def:
            command_def = ui.commandDefinitions.addButtonDefinition(
                CMD_ID, CMD_NAME, CMD_DESC
            )

        on_created = GenerateCommandCreatedHandler()
        command_def.commandCreated.add(on_created)
        handlers.append(on_created)

        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        control = panel.controls.itemById(CMD_ID)
        if not control:
            panel.controls.addCommand(command_def)
    except Exception:
        if ui:
            _show_message(ui, f"Failed to start add-in:\n{traceback.format_exc()}")


def stop(_context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        workspace = ui.workspaces.itemById(WORKSPACE_ID)
        panel = workspace.toolbarPanels.itemById(PANEL_ID)
        control = panel.controls.itemById(CMD_ID)
        if control:
            control.deleteMe()

        command_def = ui.commandDefinitions.itemById(CMD_ID)
        if command_def:
            command_def.deleteMe()
    except Exception:
        if ui:
            _show_message(ui, f"Failed to stop add-in:\n{traceback.format_exc()}")

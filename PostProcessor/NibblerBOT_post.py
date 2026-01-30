# ***************************************************************************
# *   Copyright (c) 2014 sliptonic <shopinthewoods@gmail.com>               *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

import FreeCAD
from FreeCAD import Units
import Path
import argparse
import datetime
import shlex
import Path.Post.Utils as PostUtils
import PathScripts.PathUtils as PathUtils
import tkinter as tk
from tkinter import simpledialog
import requests
import re, os

selected_username = None  # Variable to store the selected username

try:
    import PySide  # Use the FreeCAD wrapper
except ImportError:
    try:
        import PySide6  # Outside FreeCAD, try Qt6 first

        PySide = PySide6
    except ImportError:
        import PySide2  # Fall back to Qt5 (if this fails, Python will kill this module's import)

        PySide = PySide2

from PySide import QtCore, QtGui, QtWidgets

TOOLTIP = """
This is a postprocessor file for the Path workbench. It is used to
take a pseudo-G-code fragment outputted by a Path object, and output
real G-code suitable for a linuxcnc 3 axis mill. This postprocessor, once placed
in the appropriate PathScripts folder, can be used directly from inside
FreeCAD, via the GUI importer or via python scripts with:

import linuxcnc_post
linuxcnc_post.export(object,"/path/to/file.ncc","")
"""

now = datetime.datetime.now()

parser = argparse.ArgumentParser(prog="linuxcnc", add_help=False)
parser.add_argument("--no-header", action="store_true", help="suppress header output")
parser.add_argument(
    "--no-comments", action="store_true", help="suppress comment output"
)
parser.add_argument(
    "--line-numbers", action="store_true", help="prefix with line numbers"
)
parser.add_argument(
    "--no-show-editor",
    action="store_true",
    help="don't pop up editor before writing output",
)
parser.add_argument(
    "--precision", default="3", help="number of digits of precision, default=3"
)
parser.add_argument(
    "--preamble",
    help='set commands to be issued before the first command, default="G17\nG90"',
)
parser.add_argument(
    "--postamble",
    help='set commands to be issued after the last command, default="M05\nG17 G90\nM2"',
)
parser.add_argument(
    "--inches", action="store_true", help="Convert output for US imperial mode (G20)"
)
parser.add_argument(
    "--modal",
    action="store_true",
    help="Output the Same G-command Name USE NonModal Mode",
)
parser.add_argument(
    "--axis-modal", action="store_true", help="Output the Same Axis Value Mode"
)
parser.add_argument(
    "--no-tlo",
    action="store_true",
    help="suppress tool length offset (G43) following tool changes",
)

parser.add_argument(
    "--measure-tool",
    action="store_true",
    help="Measure each tool used at the beginning of the program when block delete is turned off.",
)

parser.add_argument(
    "--job-author", help="Job Author, used when posting to remote machine"
)

parser.add_argument(
    "--no-remote-post", action="store_true", help="Don't post to remote machine"
)

TOOLTIP_ARGS = parser.format_help()

# These globals set common customization preferences
OUTPUT_COMMENTS = True
OUTPUT_HEADER = True
OUTPUT_LINE_NUMBERS = False
SHOW_EDITOR = True
MODAL = False  # if true commands are suppressed if the same as previous line.
USE_TLO = True  # if true G43 will be output following tool changes
OUTPUT_DOUBLES = (
    True  # if false duplicate axis values are suppressed if the same as previous line.
)
MEASURE_TOOL = False
COMMAND_SPACE = " "
LINENR = 100  # line number starting value

# These globals will be reflected in the Machine configuration of the project
UNITS = "G21"  # G21 for metric, G20 for us standard
UNIT_SPEED_FORMAT = "mm/min"
UNIT_FORMAT = "mm"

MACHINE_NAME = "LinuxCNC"
CORNER_MIN = {"x": 0, "y": 0, "z": 0}
CORNER_MAX = {"x": 500, "y": 300, "z": 300}
PRECISION = 3

REMOTE_POST = True
JOB_AUTHOR = ""
BASE_URL = "https://nibblerbot.knoxmakers.org:1337/"


# Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = """G17 G54 G40 G49 G80 G90"""

# Postamble text will appear following the last operation.
POSTAMBLE = """M05
G17 G54 G90 G80 G40
M300
M2
"""
blockDelete = False

# Pre operation text will be inserted before every operation
PRE_OPERATION = """"""

# Post operation text will be inserted after every operation
POST_OPERATION = """"""

# Tool Change commands will be inserted before a tool change
TOOL_CHANGE = """"""

# to distinguish python built-in open function from the one declared below
if open.__module__ in ["__builtin__", "io"]:
    pythonopen = open


def processArguments(argstring):
    global OUTPUT_HEADER
    global OUTPUT_COMMENTS
    global OUTPUT_LINE_NUMBERS
    global SHOW_EDITOR
    global PRECISION
    global PREAMBLE
    global POSTAMBLE
    global UNITS
    global UNIT_SPEED_FORMAT
    global UNIT_FORMAT
    global MODAL
    global USE_TLO
    global MEASURE_TOOL
    global OUTPUT_DOUBLES
    global JOB_AUTHOR
    global REMOTE_POST

    try:
        args = parser.parse_args(shlex.split(argstring))
        if args.no_header:
            OUTPUT_HEADER = False
        if args.no_comments:
            OUTPUT_COMMENTS = False
        if args.line_numbers:
            OUTPUT_LINE_NUMBERS = True
        if args.no_show_editor:
            SHOW_EDITOR = False
        print("Show editor = %d" % SHOW_EDITOR)
        PRECISION = args.precision
        if args.preamble is not None:
            PREAMBLE = args.preamble
        if args.postamble is not None:
            POSTAMBLE = args.postamble
        if args.inches:
            UNITS = "G20"
            UNIT_SPEED_FORMAT = "in/min"
            UNIT_FORMAT = "in"
            PRECISION = 4
        if args.modal:
            MODAL = True
        if args.no_tlo:
            USE_TLO = False
        if args.axis_modal:
            OUTPUT_DOUBLES = False
        if args.measure_tool:
            MEASURE_TOOL = True
        if args.no_remote_post:
            REMOTE_POST = False
        if args.job_author:
            JOB_AUTHOR = args.job_author

    except Exception:
        return False

    return True


def export(objectslist, filename, argstring):
    # Prompt for dust collection options before anything else
    global UNITS
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT
    global PREAMBLE, POSTAMBLE
    global blockDelete

    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])

    missing_feed_speeds = []
    for obj in objectslist:
        if hasattr(obj, "Tool"):
            tool = hasattr(obj, "Tool")
            name = getattr(obj, "Label", None)
            vert_feed = getattr(obj, "VertFeed", None)
            horiz_feed = getattr(obj, "HorizFeed", None)
            spindle_speed = getattr(obj, "SpindleSpeed", None)

            if vert_feed == 0 or horiz_feed == 0 or spindle_speed == 0:
                missing_feed_speeds.append(
                    {
                        "ToolController": tool,
                        "Name": name,
                        "VertFeed": vert_feed,
                        "HorizFeed": horiz_feed,
                        "SpindleSpeed": spindle_speed,
                    }
                )

    if missing_feed_speeds:
        dialog = QtWidgets.QDialog()
        dialog.setWindowTitle("Missing Feed/Speeds")
        dialog.resize(400, 300)
        layout = QtWidgets.QVBoxLayout(dialog)

        label = QtWidgets.QLabel(
            "The following Tool Controllers have missing feeds/speed:"
        )
        layout.addWidget(label)

        text_edit = QtWidgets.QTextEdit()
        text_edit.setReadOnly(True)
        for tc in missing_feed_speeds:
            text_edit.append(f"{tc['Name']}")
            if tc["VertFeed"] == 0:
                text_edit.append("  Missing: Vertical Feed")
            if tc["HorizFeed"] == 0:
                text_edit.append("  Missing: Horizontal Feed")
            if tc["SpindleSpeed"] == 0:
                text_edit.append("  Missing: Spindle Speed")
        layout.addWidget(text_edit)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)

        dialog.exec_()
        return None

    options_dialog = DustCollectionOptionsDialog()
    if options_dialog.exec_():
        dust_on, dust_off = options_dialog.get_options()
    else:
        print("User cancelled dust collection options dialog.")
        return None

    # Add M208 at end of PREAMBLE if dust_on is checked and not already present
    if dust_on and "M208" not in PREAMBLE:
        PREAMBLE = PREAMBLE.rstrip() + "\nM208\n"

    # Add M209 before M300 in POSTAMBLE if dust_off is checked and not already present
    if dust_off and "M209" not in POSTAMBLE:
        if "M300" in POSTAMBLE:
            POSTAMBLE = POSTAMBLE.replace("M300", "M209\nM300")

    if not processArguments(argstring):
        return None

    tool_list = set()

    for obj in objectslist:
        if not hasattr(obj, "Path"):
            print(
                "the object "
                + obj.Name
                + " is not a path. Please select only path and Compounds."
            )
            return None

    print("postprocessing...")
    gcode = ""
    blockDelete = False

    # write header
    if OUTPUT_HEADER:
        gcode += linenumber() + "(Exported by FreeCAD)\n"
        gcode += linenumber() + "(Post Processor: " + __name__ + ")\n"
        gcode += linenumber() + "(Output Time:" + str(now) + ")\n"

    # Write the preamble
    if OUTPUT_COMMENTS:
        gcode += linenumber() + "(begin preamble)\n"
    for line in PREAMBLE.splitlines(False):
        gcode += linenumber() + line + "\n"
    gcode += linenumber() + UNITS + "\n"

    for obj in objectslist:
        # Skip inactive operations
        if hasattr(obj, "Active"):
            if not obj.Active:
                continue
        if hasattr(obj, "Base") and hasattr(obj.Base, "Active"):
            if not obj.Base.Active:
                continue

        for command in PathUtils.getPathWithPlacement(obj).Commands:
            if "T" in command.Parameters:
                tool_list.add(command.Parameters["T"])

    # Output the tool list at the beginning of the G-code file
    if len(tool_list) > 0:
        gcode += linenumber() + "; List of Tools Used:\n"
        for tool in tool_list:
            gcode += linenumber() + "; Tool: {}\n".format(int(tool))

    # if len(tool_list) > 0:
    # Ensure that the last tool printed is the first one used
    #    num_tools_to_print = min(len(tool_list), 12)
    #    tool_list = list(tool_list)

    #    for i in range(num_tools_to_print):
    #        gcode += "/ " + linenumber() + "T{} M6\n".format(int(tool_list[i]))
    #        gcode += "/ " + linenumber() + "#3992=0\n"
    #        if MEASURE_TOOL:
    #            gcode += "/ " + linenumber() + "M38\n"

    for obj in objectslist:
        # Skip inactive operations
        if hasattr(obj, "Active"):
            if not obj.Active:
                continue
        if hasattr(obj, "Base") and hasattr(obj.Base, "Active"):
            if not obj.Base.Active:
                continue

        if (
            hasattr(obj, "BlockDelete")
            and obj.BlockDelete
            or hasattr(obj, "Base")
            and hasattr(obj.Base, "BlockDelete")
            and obj.Base.BlockDelete
        ):
            blockDelete = True

        if blockDelete:
            gcode += "/ "

        # do the pre_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + "(begin operation: %s)\n" % obj.Label
            if blockDelete:
                gcode += "/ "
            gcode += linenumber() + "(machine units: %s)\n" % (UNIT_SPEED_FORMAT)
        for line in PRE_OPERATION.splitlines(True):
            if blockDelete:
                gcode += "/ "
            gcode += linenumber() + line

        # get coolant mode
        coolantMode = "None"
        if (
            hasattr(obj, "CoolantMode")
            or hasattr(obj, "Base")
            and hasattr(obj.Base, "CoolantMode")
        ):
            if hasattr(obj, "CoolantMode"):
                coolantMode = obj.CoolantMode
            else:
                coolantMode = obj.Base.CoolantMode

        # turn coolant on if required
        if OUTPUT_COMMENTS:
            if not coolantMode == "None":
                if blockDelete:
                    gcode += "/ "
                gcode += linenumber() + "(Coolant On:" + coolantMode + ")\n"
        if coolantMode == "Flood":
            if blockDelete:
                gcode += "/ "
            gcode += linenumber() + "M8" + "\n"
        if coolantMode == "Mist":
            if blockDelete:
                gcode += "/ "
            gcode += linenumber() + "M7" + "\n"

        # process the operation gcode
        gcode += parse(obj)

        # do the post_op
        if OUTPUT_COMMENTS:
            if blockDelete:
                gcode += "/ "
            gcode += linenumber() + "(finish operation: %s)\n" % obj.Label
        for line in POST_OPERATION.splitlines(True):
            gcode += linenumber() + line

        # turn coolant off if required
        if not coolantMode == "None":
            if OUTPUT_COMMENTS:
                if blockDelete:
                    gcode += "/ "
                gcode += linenumber() + "(Coolant Off:" + coolantMode + ")\n"

            if blockDelete:
                gcode += "/ "
            gcode += linenumber() + "M9" + "\n"

        blockDelete = False

    # do the post_amble
    if OUTPUT_COMMENTS:
        gcode += "(begin postamble)\n"
    for line in POSTAMBLE.splitlines(True):
        gcode += linenumber() + line

    gcode = optimize_gcode(gcode, optimize=False, xy_before_z=True)

    if FreeCAD.GuiUp and SHOW_EDITOR:
        final = gcode
        if len(gcode) > 200000:
            print("Skipping editor since output is greater than 100kb")
        else:
            dia = PostUtils.GCodeEditorDialog()
            dia.editor.setText(gcode)
            result = dia.exec_()
            if result:
                final = dia.editor.toPlainText()
    else:
        final = gcode

    print("done postprocessing.")

    if not filename == "-":
        gfile = pythonopen(filename, "w")
        gfile.write(final)
        gfile.close()

    if REMOTE_POST:
        if prompt_and_upload(final, filename):
            return final
        else:
            return final

    return final


def linenumber():
    global LINENR
    if OUTPUT_LINE_NUMBERS is True:
        LINENR += 10
        return "N" + str(LINENR) + " "
    return ""


def parse(pathobj):
    global PRECISION
    global MODAL
    global OUTPUT_DOUBLES
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT
    global blockDelete

    out = ""

    lastcommand = None
    precision_string = "." + str(PRECISION) + "f"
    currLocation = {}  # keep track for no doubles

    # the order of parameters
    # linuxcnc doesn't want K properties on XY plane  Arcs need work.
    params = [
        "X",
        "Y",
        "Z",
        "A",
        "B",
        "C",
        "I",
        "J",
        "F",
        "S",
        "T",
        "Q",
        "R",
        "L",
        "H",
        "D",
        "P",
    ]
    firstmove = Path.Command("G0", {"X": -1, "Y": -1, "Z": -1, "F": 0.0})
    currLocation.update(firstmove.Parameters)  # set First location Parameters

    if hasattr(pathobj, "Group"):  # We have a compound or project.
        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(compound: " + pathobj.Label + ")\n"
        for p in pathobj.Group:
            out += parse(p)
        return out
    else:  # parsing simple path
        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            return out

        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(" + pathobj.Label + ")\n"

        for c in PathUtils.getPathWithPlacement(pathobj).Commands:
            outstring = []
            if blockDelete:
                outstring.append("/ ")

            command = c.Name
            outstring.append(command)

            # if modal: suppress the command if it is the same as the last one
            if MODAL is True:
                if command == lastcommand:
                    outstring.pop(0)

            if c.Name[0] == "(" and not OUTPUT_COMMENTS:  # command is a comment
                continue

            # Now add the remaining parameters in order
            for param in params:
                if param in c.Parameters:
                    if param == "F" and (
                        currLocation[param] != c.Parameters[param] or OUTPUT_DOUBLES
                    ):
                        if c.Name not in [
                            "G0",
                            "G00",
                        ]:  # linuxcnc doesn't use rapid speeds
                            speed = Units.Quantity(
                                c.Parameters["F"], FreeCAD.Units.Velocity
                            )
                            if speed.getValueAs(UNIT_SPEED_FORMAT) > 0.0:
                                outstring.append(
                                    param
                                    + format(
                                        float(speed.getValueAs(UNIT_SPEED_FORMAT)),
                                        precision_string,
                                    )
                                )
                        else:
                            continue
                    elif param == "T":
                        outstring.append(param + str(int(c.Parameters["T"])))
                    elif param == "H":
                        outstring.append(param + str(int(c.Parameters["H"])))
                    elif param == "D":
                        outstring.append(param + str(int(c.Parameters["D"])))
                    elif param == "S":
                        outstring.append(param + str(int(c.Parameters["S"])))
                    else:
                        if (
                            (not OUTPUT_DOUBLES)
                            and (param in currLocation)
                            and (currLocation[param] == c.Parameters[param])
                        ):
                            continue
                        else:
                            pos = Units.Quantity(
                                c.Parameters[param], FreeCAD.Units.Length
                            )
                            outstring.append(
                                param
                                + format(
                                    float(pos.getValueAs(UNIT_FORMAT)), precision_string
                                )
                            )

            # store the latest command
            lastcommand = command
            currLocation.update(c.Parameters)

            # Check for Tool Change:
            if command == "M6":
                if blockDelete:
                    out += "/ "

                # outstring.pop(0)

                # stop the spindle

                out += linenumber() + "M5\n"
                for line in TOOL_CHANGE.splitlines(True):
                    out += linenumber() + line

                # outstring.append( "M6".format(int(c.Parameters["T"])) )

                # add height offset
                if USE_TLO:
                    tool_height = "G43 H" + str(int(c.Parameters["T"]))
                    outstring.append(tool_height)

            if command == "message":
                if OUTPUT_COMMENTS is False:
                    out = []
                else:
                    outstring.pop(0)  # remove the command

            # prepend a line number and append a newline

            if len(outstring) >= 1:
                if OUTPUT_LINE_NUMBERS:
                    outstring.insert(0, (linenumber()))

                # append the line to the final output
                for w in outstring:
                    out += w + COMMAND_SPACE
                # Note: Do *not* strip `out`, since that forces the allocation
                # of a contiguous string & thus quadratic complexity.
                out += "\n"

        return out


def optimize_gcode(gcode_string, optimize=True, xy_before_z=True):
    lines = gcode_string.strip().split('\n')
    modified_lines = []
    i = 0
    process_moves = False
    buffer = []  # To store Z moves temporarily
    last_feed_rate = None  # To store the last feed rate
    last_z_position = None  # To store the last Z position

    while i < len(lines):
        line = lines[i].strip()

        # Check if the line is a comment
        is_comment = line.startswith('(') and line.endswith(')')

        # Handle tool change detection
        if 'M6' in line or ('T' in line and 'M6' in line) and not is_comment:
            process_moves = True
            modified_lines.append(line)
        elif process_moves and xy_before_z:
            # Handle combined X/Y/Z moves
            if 'Z' in line and ('X' in line or 'Y' in line) and not is_comment:
                g_code_prefix = line.split()[0]
                parts = line.split()
                xy_parts = ' '.join(
                    [part for part in parts if 'X' in part or 'Y' in part]
                )
                z_part = ' '.join([part for part in parts if 'Z' in part])
                modified_lines.append(f"{g_code_prefix} {xy_parts}")
                modified_lines.append(f"{g_code_prefix} {z_part}")
                process_moves = False
            elif 'Z' in line and not is_comment:
                buffer.append(line)
            elif 'X' in line or 'Y' in line and not is_comment:
                modified_lines.append(line)
                modified_lines.extend(buffer)
                buffer = []
                process_moves = False
            else:
                if line.strip() != '' and line.strip() not in ['G0', 'G1']:
                    modified_lines.append(line)
        else:
            if optimize and not is_comment:
                if 'F' in line:
                    feed_rate_index = line.find('F')
                    if feed_rate_index != -1:
                        feed_rate = line[feed_rate_index:].split()[0]
                        current_feed_rate = ''.join(filter(str.isdigit, feed_rate))
                        if current_feed_rate == last_feed_rate:
                            line = line.replace(' ' + feed_rate, '')
                        else:
                            last_feed_rate = current_feed_rate
                if 'Z' in line:
                    z_index = line.find('Z')
                    if z_index != -1:
                        z_position = line[z_index:].split()[0]
                        current_z_position = ''.join(filter(str.isdigit, z_position))
                        if current_z_position == last_z_position:
                            line = line.replace(' ' + z_position, '')
                        else:
                            last_z_position = current_z_position

            if line.strip() != '' and line.strip() not in ['G0', 'G1']:
                modified_lines.append(line)
        i += 1

    # Append any remaining buffered Z moves
    if buffer:
        modified_lines.extend(buffer)

    return '\n'.join(modified_lines)


def prompt_username_selection(usernames):
    global selected_username

    dialog = QtWidgets.QDialog()
    dialog.setWindowTitle("Select Remote User Folder")
    # dialog.setMinimumWidth(265)  # Adjusted minimum width to better fit the title

    # Create layout for the dialog
    layout = QtWidgets.QVBoxLayout(dialog)

    # Add a label
    label = QtWidgets.QLabel("Please select your user folder:")
    layout.addWidget(label)

    # Add a combo box with search functionality
    combo_box = ComboBoxWithSearch()
    combo_box.addItem("")  # Add blank entry at the beginning
    combo_box.addItems(usernames)

    # Set the initial value of the combo box to the stored username
    if selected_username in usernames:
        combo_box.setCurrentText(selected_username)

    layout.addWidget(combo_box)

    # Add the button box with centered buttons
    button_box = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
    )
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    # Customize the button text
    button_box.button(QtWidgets.QDialogButtonBox.Ok).setText("Select")

    # Add button box to layout, center it horizontally
    layout.addWidget(button_box, alignment=QtCore.Qt.AlignHCenter)

    # Set the layout and execute the dialog
    dialog.setLayout(layout)

    if dialog.exec_():
        # Retrieve the selected username
        selected_username = combo_box.currentText()
    else:
        selected_username = None

    return selected_username


class FileManagerDialog(QtWidgets.QDialog):
    def __init__(self, username, file_content, filename):
        super().__init__()
        self.username = username
        self.file_content = file_content
        self.filename = filename
        self.current_path = "/"

        self.setWindowTitle("Select Directory and File Name")
        self.setLayout(QtWidgets.QVBoxLayout())

        # # Navigate Up Button
        # self.navigate_up_button = QtWidgets.QPushButton()
        # self.navigate_up_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_ArrowUp))
        # self.navigate_up_button.setFixedSize(24, 24)  # Button size matches icon size
        # self.navigate_up_button.clicked.connect(self.navigate_up)
        # self.layout().addWidget(self.navigate_up_button, alignment=QtCore.Qt.AlignLeft)

        # File Manager Tree View
        self.file_list = QtWidgets.QTreeView()
        self.file_list.setRootIsDecorated(False)  # No tree expand/collapse indicators
        self.file_list.setAlternatingRowColors(True)  # For better row visibility
        self.file_list.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows
        )  # Row-based selection
        self.file_list.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers
        )  # Disable editing
        self.layout().addWidget(self.file_list)

        # Connect double-click signal to handler
        self.file_list.doubleClicked.connect(self.handle_item_double_click)
        self.file_list.clicked.connect(self.handle_single_click)

        # Custom Sort Model for Sorting
        self.model = QtGui.QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Name", "Date Modified", "Size"])

        self.proxy_model = CustomSortModel()
        self.proxy_model.setSourceModel(self.model)
        self.file_list.setModel(self.proxy_model)

        self.file_list.setColumnWidth(0, 300)  # Name column
        self.file_list.setColumnWidth(1, 150)  # Date Modified column
        self.file_list.setColumnWidth(2, 100)  # Size column

        # Enable sorting and set default sort order
        self.file_list.setSortingEnabled(True)
        self.file_list.sortByColumn(
            1, QtCore.Qt.DescendingOrder
        )  # Default to sorting by "Date Modified" in descending order

        # File Name Input
        self.file_name_input = QtWidgets.QLineEdit(self.filename)
        self.layout().addWidget(QtWidgets.QLabel("File Name:"))
        self.layout().addWidget(self.file_name_input)

        # Buttons
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.handle_save)
        button_box.rejected.connect(self.reject)
        self.layout().addWidget(button_box)

        self.resize(650, 400)  # Initial size of the dialog
        self.refresh_file_list()

    def fetch_files(self):
        url = f"{BASE_URL}api/v1/files/list.php"
        data = {'user': self.username, 'location': self.current_path}
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                return data['data']
        except requests.RequestException as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Error fetching files: {e}")
        return {}

    def refresh_file_list(self):
        self.model.removeRows(0, self.model.rowCount())  # Clear the model

        data = self.fetch_files()
        if not isinstance(data, dict):
            QtWidgets.QMessageBox.critical(
                self, "Error", "Invalid data format received from API."
            )
            return

        dirs = data.get('dirs', [])
        files = data.get('files', [])

        folder_icon = self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon)
        file_icon = self.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)

        # Add "Navigate Up" row if not at the root level
        if self.current_path != "/":
            navigate_up_item = QtGui.QStandardItem(folder_icon, "..")
            navigate_up_item.setEditable(False)
            self.model.appendRow(
                [navigate_up_item, QtGui.QStandardItem(""), QtGui.QStandardItem("")]
            )

        # Sort directories alphabetically
        dirs.sort(key=str.lower)

        # Add directories
        for directory in dirs:
            folder_item = QtGui.QStandardItem(folder_icon, directory)
            folder_item.setEditable(False)
            # Size column intentionally left empty for folders
            self.model.appendRow(
                [folder_item, QtGui.QStandardItem(""), QtGui.QStandardItem("")]
            )

        # Add files
        for file in files:
            name = file.get('name', 'Unknown')
            date = file.get('date', '')
            time = file.get('time', '')
            size = file.get('size', '')

            date_modified = f"{date} {time}".strip()

            file_item = QtGui.QStandardItem(file_icon, name)
            file_item.setEditable(False)
            date_item = QtGui.QStandardItem(date_modified)
            size_str = file.get('size', '')
            # Add space between digits and size indicator
            size_str = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', size_str.strip())
            # size_str = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', size_str.strip()).lower().replace('b', 'bytes')
            size_str = re.sub(
                r'\bB\b', 'bytes', size_str
            )  # Replace standalone 'B' with 'BYTES'
            size_item = QtGui.QStandardItem(size_str)
            self.model.appendRow([file_item, date_item, size_item])

        self.file_list.clearSelection()
        self.file_name_input.setFocus()

    def handle_item_double_click(self, index):
        source_index = self.proxy_model.mapToSource(
            index
        )  # Map proxy index to source model index
        row = source_index.row()  # Get the row number

        # Retrieve the first column item (representing the main identifier, e.g., folder or file name)
        item = self.model.item(
            row, 0
        )  # Assuming column 0 is where the main name or ".." resides
        if not item:
            return

        item_name = item.text()

        # Check if it's the "Navigate Up" row
        if item_name == "..":
            if self.current_path != "/":
                self.current_path = os.path.dirname(self.current_path.rstrip("/"))
                if not self.current_path:
                    self.current_path = "/"
                self.refresh_file_list()
        else:
            # Handle folder or file selection
            # Assume column 2 contains the "Date Modified" to differentiate folders from files
            is_folder = not self.model.item(row, 1).text()
            if is_folder:
                self.current_path = os.path.join(self.current_path, item_name).replace(
                    "\\", "/"
                )
                self.refresh_file_list()
            else:
                self.file_name_input.setText(item_name)
                self.handle_save()

    def handle_single_click(self, index):
        source_index = self.proxy_model.mapToSource(
            index
        )  # Map proxy index to source model index
        row = source_index.row()  # Get the row number

        # Retrieve the first column item (representing the main identifier, e.g., folder or file name)
        item = self.model.item(
            row, 0
        )  # Assuming column 0 is where the main name or ".." resides
        if not item:
            return

        item_name = item.text()

        # Handle folder or file selection
        # Assume column 2 contains the "Date Modified" to differentiate folders from files
        is_folder = not self.model.item(row, 1).text()
        if not is_folder:
            self.file_name_input.setText(item_name)
            self.file_name_input.setFocus()

    def navigate_up(self):
        if self.current_path != "/":
            self.current_path = os.path.dirname(self.current_path.rstrip("/"))
            if not self.current_path:
                self.current_path = "/"
            self.refresh_file_list()

    def prompt_overwrite(self):
        response = QtWidgets.QMessageBox.question(
            self,
            "Overwrite File",
            "File already exists. Do you want to overwrite it?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if response == QtWidgets.QMessageBox.Yes:
            self.accept()

    def handle_save(self):
        proxy_model = self.file_list.model()  # Get the proxy model
        source_model = proxy_model.sourceModel()  # Access the underlying source model
        root_node = (
            source_model.invisibleRootItem()
        )  # Get the root node of the source model
        number_of_files = root_node.rowCount()

        existing_files = []
        for i in range(number_of_files):
            file_item = root_node.child(
                i, 0
            )  # Assuming file names are in the second column
            if file_item:
                file_name = file_item.text()
                existing_files.append(file_name)

        input_file_name = self.file_name_input.text()
        if input_file_name in existing_files:
            self.prompt_overwrite()
        else:
            self.accept()


def prompt_and_upload(file_content, filename):
    # app = QtWidgets.QApplication([])

    usernames = fetch_usernames()
    if not usernames:
        print("Error fetching usernames or no usernames available.")
        return False

    # Prompt for username
    # username = simpledialog.askstring("Input", "Please enter your username:", parent=root)
    if JOB_AUTHOR == "":
        username = prompt_username_selection(usernames)
    else:
        username = JOB_AUTHOR

    if not username:
        print("No username provided. Upload cancelled.")
        return False

    filename = FreeCAD.ActiveDocument.FileName
    filename = filename.split('/')[-1] if '/' in filename else filename.split('\\')[-1]
    if filename.endswith('.FCStd'):
        filename = filename.replace('.FCStd', '.ngc')

    print("Filename:", filename)

    dialog = FileManagerDialog(username, file_content, filename)
    if dialog.exec_():
        selected_path = dialog.current_path
        selected_file_name = dialog.file_name_input.text()
        if not selected_file_name:
            print("No file name provided. Upload cancelled.")
            return False

        response = upload_file(
            username, file_content, selected_file_name, selected_path
        )
        if response.status_code == 200:
            print("Upload successful!")
            return True
        else:
            print("Upload failed!", response.status_code, response.text)
            return False


def upload_file(username, file_content, filename, path):
    url = f"{BASE_URL}api/v1/plugins/upload"
    files = {'fileUpload': (filename, file_content, 'text/plain')}
    data = {
        'user': username,
        'location': path,
        'uploader': 'direct',
        'filename': filename,
        'config': '{}',
        'options': '{}',
    }
    return requests.post(url, files=files, data=data)


def fetch_usernames():
    url = f"{BASE_URL}api/v1/users/list"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 1:
            return data['data']
    except requests.RequestException as e:
        print(f"Error fetching usernames: {e}")
    return []


class CustomSortModel(QtCore.QSortFilterProxyModel):
    def __init__(self, sort_column=1, *args, **kwargs):  # Default sort by name
        super(CustomSortModel, self).__init__(*args, **kwargs)
        self.sort_column = 1  # Default sort by name

    def sort(self, column, order=QtCore.Qt.AscendingOrder):
        self.sort_column = column
        super().sort(column, order)  # Call

    def lessThan(self, left, right):
        # Check if the item is a folder or a file based on the 'Date Modified' (typically, folders might have this empty)
        left_date = self.sourceModel().data(
            left.sibling(left.row(), 1), QtCore.Qt.DisplayRole
        )
        right_date = self.sourceModel().data(
            right.sibling(right.row(), 1), QtCore.Qt.DisplayRole
        )

        left_is_folder = not left_date
        right_is_folder = not right_date

        # Folders come before files
        if left_is_folder or right_is_folder:
            return False

        # Sorting by the designated column when both are either files or folders
        if self.sort_column == 0:  # Sort by name
            left_data = self.sourceModel().data(
                left.sibling(left.row(), 0), QtCore.Qt.DisplayRole
            )
            right_data = self.sourceModel().data(
                right.sibling(right.row(), 0), QtCore.Qt.DisplayRole
            )
        elif self.sort_column == 1:  # Sort by date
            left_data = QtCore.QDateTime.fromString(left_date, "yyyy-MM-dd HH:mm:ss")
            right_data = QtCore.QDateTime.fromString(right_date, "yyyy-MM-dd HH:mm:ss")
        elif self.sort_column == 2:  # Sort by size
            left_data = self.extract_size(
                self.sourceModel().data(
                    left.sibling(left.row(), 2), QtCore.Qt.DisplayRole
                )
            )
            right_data = self.extract_size(
                self.sourceModel().data(
                    right.sibling(right.row(), 2), QtCore.Qt.DisplayRole
                )
            )
        else:
            return False  # Default fallback

        return left_data < right_data

    def extract_size(self, size_str):
        if not size_str:
            return 0  # Assume empty or 'N/A' for folders

        size_str = size_str.strip().upper()
        if 'KB' in size_str:
            return float(size_str.replace('KB', '').strip()) * 1024
        elif 'MB' in size_str:
            return float(size_str.replace('MB', '').strip()) * 1024 * 1024
        elif 'GB' in size_str:
            return float(size_str.replace('GB', '').strip()) * 1024 * 1024 * 1024
        elif 'TB' in size_str:
            return float(size_str.replace('TB', '').strip()) * 1024 * 1024 * 1024 * 1024
        elif 'BYTES' in size_str:
            return float(size_str.replace('BYTES', '').strip())
        else:
            return float(size_str)  # Assume bytes if no unit is specified


class ComboBoxWithSearch(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setEditable(True)
        self.setInsertPolicy(QtWidgets.QComboBox.NoInsert)

        self.completer = QtWidgets.QCompleter(self)
        self.setCompleter(self.completer)
        self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)

        self.set_model(QtGui.QStandardItemModel())
        self.completer.setModel(self.model())

    def set_model(self, model):
        self.clear()
        self.setModel(model)

    def addItems(self, items):
        for item in items:
            self.addItem(item)


class DustCollectionOptionsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dust Collection Options")
        self.setLayout(QtWidgets.QVBoxLayout())

        self.start_checkbox = QtWidgets.QCheckBox(
            "Turn Dust Collection ON at Start (M208)"
        )
        self.start_checkbox.setChecked(True)
        self.layout().addWidget(self.start_checkbox)

        self.end_checkbox = QtWidgets.QCheckBox(
            "Turn Dust Collection OFF at End (M209)"
        )
        self.end_checkbox.setChecked(False)
        self.layout().addWidget(self.end_checkbox)

        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout().addWidget(button_box)

    def get_options(self):
        return self.start_checkbox.isChecked(), self.end_checkbox.isChecked()

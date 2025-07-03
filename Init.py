# -*- coding: utf-8 -*-
"""NibblerBOT Init: install-once-per-commit via Git hash (repo = addon dir)."""

import sys
import os
import inspect
import subprocess
import FreeCAD

# locate this Init.py
_this_file = inspect.getfile(inspect.currentframe())
addon_dir  = os.path.dirname(_this_file)
FreeCAD.Console.PrintMessage(f"– Init running from: {addon_dir}\n")

# make sure we can import install.py
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)

def auto_update_repo(path):
    FreeCAD.Console.PrintMessage("– Auto-updating NibblerBOT via git pull…\n")
    try:
        out = subprocess.check_output(
            ["git", "pull", "--ff-only"],
            cwd=path,
            stderr=subprocess.STDOUT
        )
        FreeCAD.Console.PrintMessage(out.decode("utf-8"))
    except Exception as e:
        FreeCAD.Console.PrintError(f"Auto-update failed: {e}\n")

auto_update_repo(addon_dir)

# helper: get the current short commit hash from addon_dir
def get_git_hash(path):
    FreeCAD.Console.PrintMessage(f"– Using Git cwd: {path}\n")
    try:
        # change directory and run git in one shell command
        cmd = f'cd "{path}" && git rev-parse --short HEAD'
        result = os.popen(cmd).read().strip()
        if result:
            return result
        else:
            FreeCAD.Console.PrintMessage("os.popen returned empty; no hash found\n")
    except Exception as e:
        FreeCAD.Console.PrintError(f"os.popen fallback failed: {e}\n")

# fetch and show the current hash (or “unknown”)
current_hash = get_git_hash(addon_dir) or "unknown"
FreeCAD.Console.PrintMessage(f"– Current hash: {current_hash}\n")

# load stored hash from prefs
prefs     = FreeCAD.ParamGet("User parameter:NibblerBOT")
last_hash = prefs.GetString("LastInstalledHash", "")
FreeCAD.Console.PrintMessage(f"– Last hash   : {last_hash}\n")

# run installer only if the hash changed
if last_hash != current_hash:
    try:
        import install
        prefs.SetString("LastInstalledHash", current_hash)
        FreeCAD.Console.PrintMessage(
            f"NibblerBOT: installed commit {current_hash}\n"
        )
    except Exception as e:
        FreeCAD.Console.PrintError(f"NibblerBOT install error: {e}\n")
else:
    FreeCAD.Console.PrintMessage(
        f"NibblerBOT: commit {current_hash} already installed\n"
    )


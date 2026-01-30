# -*- coding: utf-8 -*-
"""Knox Makers FreeCAD Manager Init: install-once-per-commit via Git hash (repo = addon dir)."""

import sys
import os
import inspect
import FreeCAD

# locate this Init.py
_this_file = inspect.getfile(inspect.currentframe())
addon_dir = os.path.dirname(_this_file)
FreeCAD.Console.PrintMessage(f"– Init running from: {addon_dir}\n")

# make sure we can import install.py
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)


def auto_update_repo(path):
    FreeCAD.Console.PrintMessage("– Auto-updating FreeCAD manager via git pull…\n")
    try:
        cmd = f'cd "{path}" && git pull --ff-only'
        result = os.popen(cmd).read()
        FreeCAD.Console.PrintMessage(result)
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
prefs = FreeCAD.ParamGet(
    "User parameter:BaseApp/Preferences/Mod/KnoxMakersFreeCADManager"
)
last_hash = prefs.GetString("LastInstalledHash", "")
FreeCAD.Console.PrintMessage(f"– Last hash   : {last_hash}\n")

# check FreeCAD version
version = FreeCAD.Version()
major = int(version[0])
minor = int(version[1])
current_version = f"v{major}-{minor}"

# check installed version history
installed_versions = prefs.GetString("InstalledVersions", "")
FreeCAD.Console.PrintMessage(f"– Current version: {current_version}\n")
FreeCAD.Console.PrintMessage(f"– Installed versions: {installed_versions}\n")

# parse version list and check if current version has been installed
version_list = [v.strip() for v in installed_versions.split(",") if v.strip()]
version_already_installed = current_version in version_list

# run installer if hash changed OR version not yet installed
needs_install = last_hash != current_hash or not version_already_installed

if needs_install:
    try:
        import install

        prefs.SetString("LastInstalledHash", current_hash)

        # add current version to history if not already present
        if current_version not in version_list:
            version_list.append(current_version)
            prefs.SetString("InstalledVersions", ",".join(version_list))

        FreeCAD.Console.PrintMessage(
            f"Knox Makers FreeCAD Manager: installed commit {current_hash} for {current_version}\n"
        )
    except Exception as e:
        FreeCAD.Console.PrintError(f"Knox Makers FreeCAD Manager install error: {e}\n")
else:
    FreeCAD.Console.PrintMessage(
        f"Knox Makers FreeCAD Manager: commit {current_hash} already installed for {current_version}\n"
    )

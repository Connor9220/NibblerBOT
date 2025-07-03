"""NibblerBOT Init: installs CAM tools & templates on FreeCAD startup."""

import sys
import os
import FreeCAD

module_path = os.path.dirname(__file__)
if module_path not in sys.path:
    sys.path.append(module_path)

from NibblerBOT import install

install.install()

# 3. (Optional) Add a button to re-install on demand
try:
    import FreeCADGui

    class InstallCAMToolsCommand:
        """Re-run CAM tools installer."""

        def Activated(self):
            install.install()
            FreeCAD.Console.PrintMessage("Re-installed NibblerBOT Tools.\n")

        def GetResources(self):
            return {
                "MenuText": "Reinstall NibblerBOT Tools",
                "ToolTip": "Copy your .fctb and templates into the CAM folders",
                # 'Pixmap': 'path/to/icon.svg'
            }

    FreeCADGui.addCommand("NibblerBOT_Reinstall", InstallCAMToolsCommand())
except ImportError:
    pass

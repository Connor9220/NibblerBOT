# NibblerBOT FreeCAD Plugin

This plugin provides an integrated environment for working with the NibblerBOT CNC machine at Knox Makers. It ensures users have an up-to-date set of tools, post processor, job templates, and preferences for seamless operation within FreeCAD.

## Features

- **Automatic Updates:** Keeps the plugin and its resources up-to-date using Git.
- **Post Processor:** Includes a custom post processor for generating G-code compatible with the NibblerBOT CNC.
- **Job Templates:** Provides pre-defined job templates for common 2D engraving and panel operations.
- **Preference Pack:** Installs a PreferencePack for consistent configuration across users.
- **Tool Libraries:** Ships with a library of tool definitions and shapes for use in FreeCAD Path workbench.

## Directory Structure

```
Init.py
install.py
job_NibblerBOT*.json
PostProcessor/
  NibblerBOT_post.py
PreferencePack/
  NibblerBOT/
    NibblerBOT.cfg
Tools/
  Bit/
  Library/
  Shape/
```

## Installation

1. Clone or download this repository into your FreeCAD `Mod` directory.
2. Start FreeCAD. The plugin will automatically check for updates and install required files.
3. The post processor, job templates, and tools will be available in the Path workbench.

## Usage

- Select the NibblerBOT post processor when exporting G-code.
- Use the provided job templates for quick setup.
- Tool definitions and shapes are available under the `Tools` directory.

## About

This plugin is maintained by Knox Makers for the NibblerBOT CNC machine. For questions or contributions, please contact the Knox Makers
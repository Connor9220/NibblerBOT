# Knox Makers FreeCAD Manager

  This addon provides a centralized way to manage themes, preferences, UI settings, and startup behavior across all FreeCAD installations at Knox Makers. It includes support for CNC machines at Knox Makers with up-to-date tool libraries, job templates, and custom post processors. Designed to keep laptops, shop machines, and individual users in sync, it ensures a shared and streamlined FreeCAD experience throughout the makerspace.

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

This plugin is maintained by Knox Makers. For questions or contributions, please contact the maintainer at Knox Makers.
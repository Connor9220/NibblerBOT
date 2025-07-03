import FreeCAD, os, shutil

# Get FreeCAD preferences
prefs = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/Mod/CAM")

# Get user's home directory
home_dir = os.path.expanduser("~")
freecad_dir = os.path.join(home_dir, "Documents", "FreeCAD")

# Ensure FreeCAD directory exists
if not os.path.exists(freecad_dir):
    os.makedirs(freecad_dir)
    print(f"Created FreeCAD directory at: {freecad_dir}")

# Define default paths
tool_bit_dir = os.path.join(freecad_dir, "Tools", "Bit")
tool_lib_dir = os.path.join(freecad_dir, "Tools", "Library")
tool_shape_dir = os.path.join(freecad_dir, "Tools", "Shape")
tools_root_dir = os.path.join(freecad_dir, "Tools")  # Root of Tools directory
default_tool_lib_file = os.path.join(tools_root_dir, "Library.fctl")
gcode_dir = os.path.join(freecad_dir, "Gcode")  # Gcode directory

# Ensure directories exist
for path in [tool_bit_dir, tool_lib_dir, tool_shape_dir, gcode_dir]:
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

# Check and set preferences
if not prefs.GetString("LastPathToolBit"):
    prefs.SetString("LastPathToolBit", tool_bit_dir)
    print(f"Set LastPathToolBit to: {tool_bit_dir}")

if not prefs.GetString("LastPathToolLibrary"):
    prefs.SetString("LastPathToolLibrary", tool_lib_dir)
    print(f"Set LastPathToolLibrary to: {tool_lib_dir}")

if not prefs.GetString("LastPathToolShape"):
    prefs.SetString("LastPathToolShape", tool_shape_dir)
    print(f"Set LastPathToolShape to: {tool_shape_dir}")

if not prefs.GetString("DefaultFilePath"):
    prefs.SetString("DefaultFilePath", default_tool_lib_file)
    print(f"Set DefaultFilePath to: {default_tool_lib_file}")

# Set PostProcessor preferences
post_processor_blacklist = [
    "KineticNCBeamicon2",
    "centroid",
    "comparams",
    "dynapath",
    "estlcam",
    "fablin",
    "fangling",
    "fanuc",
    "generic",
    "heidenhain",
    "jtech",
    "mach3_mach4",
    "marlin",
    "nccad",
    "opensbp",
    "philips",
    "refactored_centroid",
    "refactored_grbl",
    "refactored_linuxcnc",
    "refactored_mach3_mach4",
    "refactored_test",
    "rml",
    "rrf",
    "smoothie",
    "uccnc",
    "wedm",
]
if not prefs.GetString("PostProcessorBlacklist"):
    prefs.SetString("PostProcessorBlacklist", str(post_processor_blacklist))
    print(f"Set PostProcessorBlacklist to: {post_processor_blacklist}")

post_processor_output_file = os.path.join(gcode_dir, "%d.ngc")
if not prefs.GetString("PostProcessorOutputFile"):
    prefs.SetString("PostProcessorOutputFile", post_processor_output_file)
    print(f"Set PostProcessorOutputFile to: {post_processor_output_file}")

lib_area_curve_accuracy = 0.010160000000
if not prefs.GetFloat("LibAreaCurveAccuracy"):
    prefs.SetFloat("LibAreaCurveAccuracy", lib_area_curve_accuracy)
    print(f"Set LibAreaCurveAccuracy to: {lib_area_curve_accuracy}")

geometry_tolerance = 0.010160000000
if not prefs.GetFloat("GeometryTolerance"):
    prefs.SetFloat("GeometryTolerance", geometry_tolerance)
    print(f"Set GeometryTolerance to: {geometry_tolerance}")

post_processor_default = "NibblerBot"
if not prefs.GetString("PostProcessorDefault"):
    prefs.SetString("PostProcessorDefault", post_processor_default)
    print(f"Set PostProcessorDefault to: {post_processor_default}")

# Copy all files from source directories to target directories
source_dir = os.path.dirname(__file__)  # Directory containing this script
source_subdirs = {
    "Tools/Bit": tool_bit_dir,
    "Tools/Library": tool_lib_dir,
    "Tools/Shape": tool_shape_dir,
}

for subdir, destination in source_subdirs.items():
    source_path = os.path.join(source_dir, subdir)
    if os.path.exists(source_path):
        for filename in os.listdir(source_path):
            file_path = os.path.join(source_path, filename)
            if os.path.isfile(file_path):  # Only copy files, not subdirectories
                shutil.copy(file_path, destination)
                print(f"Copied {filename} to {destination}")
    else:
        print(f"Source directory not found: {source_path}. Skipping.")

# Handle Library.fctl separately
library_file_source = os.path.join(source_dir, "Tools", "Library.fctl")
if os.path.exists(library_file_source):
    shutil.copy(library_file_source, tools_root_dir)
    print(f"Copied Library.fctl to {tools_root_dir}")
else:
    print(f"Library.fctl not found in {os.path.join(source_dir, 'Tools')}. Skipping.")

# Handle Post Processor
macro_dir = os.path.join(FreeCAD.getUserAppDataDir(), "Macro")
if not os.path.exists(macro_dir):
    os.makedirs(macro_dir)
    print(f"Created Macro directory at: {macro_dir}")

post_processor_source = os.path.join(source_dir, "PostProcessor", "NibblerBot_post.py")
if os.path.exists(post_processor_source):
    shutil.copy(post_processor_source, macro_dir)
    print(f"Copied Post Processor to {macro_dir}")
else:
    print(f"Post Processor not found at {post_processor_source}. Skipping.")

# Handle job_NibblerBot.json
job_file_source = os.path.join(source_dir, "job_NibblerBot.json")
if os.path.exists(job_file_source):
    shutil.copy(job_file_source, freecad_dir)
    print(f"Copied job_NibblerBot.json to {freecad_dir}")
else:
    print(f"job_NibblerBot.json not found at {job_file_source}. Skipping.")

print("Installation complete!")

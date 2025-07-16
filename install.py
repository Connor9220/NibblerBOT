import FreeCAD, os, shutil, json

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
default_tool_lib_file = os.path.join(tool_lib_dir, "NibblerBOT.fctl")
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
    prefs.SetString("DefaultFilePath", freecad_dir)
    print(f"Set DefaultFilePath to: {freecad_dir}")

if not prefs.GetString("LastFileToolLibrary"):
    prefs.SetString("LastFileToolLibrary", default_tool_lib_file)
    print(f"Set LastFileToolLibrary to: {default_tool_lib_file}")


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

post_processor_default = "NibblerBOT"
if not prefs.GetString("PostProcessorDefault"):
    prefs.SetString("PostProcessorDefault", post_processor_default)
    print(f"Set PostProcessorDefault to: {post_processor_default}")

# Copy all files from source directories to target directories
source_dir = os.path.dirname(__file__)  # Directory containing this script
source_subdirs = {
    "Tools/Bit": tool_bit_dir,
    "Tools/Library": tool_lib_dir,
    "Tools/Shape": tool_shape_dir,
    "PostProcessor": os.path.join(FreeCAD.getUserAppDataDir(), "Macro"),
    "jobs": freecad_dir,
}

manifest_path = os.path.join(freecad_dir, ".nibbler_manifest.json")

def load_manifest():
    if os.path.exists(manifest_path):
        with open(manifest_path, "r") as f:
            return json.load(f)
    return {}

def save_manifest(manifest):
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

def sync_group(source_path, target_path, group_name, file_filter=None):
    manifest = load_manifest()
    managed_files = set(manifest.get(group_name, []))
    source_files = set(
        f for f in os.listdir(source_path)
        if os.path.isfile(os.path.join(source_path, f)) and (file_filter(f) if file_filter else True)
    )

    # Remove files that were managed but no longer exist in source
    for filename in managed_files - source_files:
        target_file = os.path.join(target_path, filename)
        if os.path.exists(target_file):
            os.remove(target_file)
            print(f"Removed {filename} from {target_path}")

    # Copy new/updated files from source
    for filename in source_files:
        src_file = os.path.join(source_path, filename)
        dst_file = os.path.join(target_path, filename)
        shutil.copy(src_file, dst_file)
        print(f"Copied {filename} to {target_path}")

    # Update manifest
    manifest[group_name] = list(source_files)
    save_manifest(manifest)

# Sync tool directories
for subdir, destination in list(source_subdirs.items())[:3]:
    source_path = os.path.join(source_dir, subdir)
    if os.path.exists(source_path):
        sync_group(source_path, destination, subdir)
    else:
        print(f"Source directory not found: {source_path}. Skipping.")

# Sync PostProcessor directory
post_processor_source = os.path.join(source_dir, "PostProcessor")
if os.path.exists(post_processor_source):
    sync_group(post_processor_source, source_subdirs["PostProcessor"], "PostProcessor")
else:
    print(f"PostProcessor directory not found: {post_processor_source}. Skipping.")

# Sync job_*.json files in root
def job_file_filter(filename):
    return filename.startswith("job_") and filename.endswith(".json")

sync_group(source_dir, source_subdirs["jobs"], "jobs", file_filter=job_file_filter)

print("Installation complete!")

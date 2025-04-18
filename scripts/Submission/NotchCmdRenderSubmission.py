from Deadline.Scripting import ClientUtils
from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog
from Deadline.Scripting import RepositoryUtils

import os
import re
import time
from pathlib import Path

# File extension definitions
ALLOWED_SCENE_EXTENSIONS = ['.dfx']  # Notch project files
ALLOWED_OUTPUT_EXTENSIONS = {
    "notchlc": [".mov"],
    "h264": [".mp4"],
    "h265": [".mp4"],
    "hap": [".mov"],
    "mov": [".mov"],
    "exr": [".exr"],
    "png": [".png"],
    "jpg": [".jpg", ".jpeg"],
    "tga": [".tga"],
    "tiff": [".tif", ".tiff"]
}

# Image codecs that require individual frames
IMAGE_CODECS = {"exr", "png", "jpg", "tga", "tiff"}

# Default paths
user_documents = os.path.join(os.path.expanduser("~"), "Documents")
default_log_path = os.path.join(user_documents, "NotchRenderLog.txt")


def normalize_windows_path(path):
    """Normalizes Windows paths to use correct separators"""
    return os.path.normpath(path.replace('/', '\\'))

def is_unc_path(path):
    """Check if path is a UNC path"""
    return path.startswith('\\\\')

def is_file_locked(file_path):
    """Check if file is locked/in use on Windows"""
    try:
        with open(file_path, 'a') as f:
            pass
        return False
    except IOError:
        return True

def check_windows_environment():
    """Verify Windows-specific requirements"""
    try:
        # Check if running on Windows
        if os.name != 'nt':
            return False
            
        # Check for required Windows features
        required_dirs = [
            os.environ.get('TEMP'),
            os.environ.get('SystemRoot')
        ]
        
        for dir in required_dirs:
            if not dir or not os.path.exists(dir):
                return False
                
        return True
        
    except Exception:
        return False

def is_safe_path(path):
    """
    Validates if a file path is safe to use.
    """
    try:
        # Convert to absolute path and normalize for Windows
        abs_path = os.path.abspath(normalize_windows_path(path))
        
        # Check for suspicious characters
        unsafe_chars = ['<', '>', '|', '*', '?', '"', ';', '&', '$']
        if any(char in path for char in unsafe_chars):
            print(f"⚠️ Path contains unsafe characters: {path}")
            return False
            
        # Check for relative path traversal attempts
        if '..' in path:
            print(f"⚠️ Path contains suspicious traversal patterns: {path}")
            return False
            
        # Validate path length (Windows MAX_PATH is 260)
        if len(abs_path) > 260:
            print(f"⚠️ Path exceeds maximum length: {len(abs_path)} characters")
            return False
            
        return True
        
    except Exception as e:
        print(f"⚠️ Path validation error: {e}")
        return False

def validate_resolution(width, height):
    """
    Validates render resolution.
    """
    try:
        w, h = int(width), int(height)
        if w <= 0 or h <= 0 or w > 16384 or h > 16384:  # Example max resolution
            print(f"⚠️ Invalid resolution: {w}x{h}")
            return False
        return True
    except ValueError:
        print("⚠️ Resolution must be numeric")
        return False

def validate_file_extension(filename, allowed_extensions):
    """Validates if a file has an allowed extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        print(f"⚠️ Invalid file extension: {ext}. Allowed: {', '.join(allowed_extensions)}")
        return False
    return True

def sanitize_filename(filename):
    """
    Sanitizes a filename by removing or replacing unsafe characters.
    """
    # Remove or replace unsafe characters
    unsafe_chars = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
    sanitized = unsafe_chars.sub('_', filename)
    
    # Ensure filename isn't too long
    max_length = 255
    name, ext = os.path.splitext(sanitized)
    if len(sanitized) > max_length:
        sanitized = name[:max_length-len(ext)] + ext
        
    return sanitized

def cleanup_temp_files(job_info_filename, plugin_info_filename):
    """Cleans up temporary files with Windows-specific handling"""
    files_to_cleanup = [
        (job_info_filename, "job info"),
        (plugin_info_filename, "plugin info")
    ]
    
    cleanup_success = True
    
    for file_path, file_type in files_to_cleanup:
        try:
            if os.path.exists(file_path):
                if is_file_locked(file_path):
                    print(f"⚠️ File is locked, retrying: {file_path}")
                    time.sleep(1)  # Wait for file to be released
                os.remove(file_path)
                print(f"✅ Cleaned up {file_type} file: {file_path}")
            else:
                print(f"ℹ️ {file_type} file not found: {file_path}")
                
        except Exception as e:
            cleanup_success = False
            print(f"⚠️ Error cleaning up {file_type} file {file_path}: {e}")
    
    return cleanup_success

# Define default log path
user_documents = os.path.join(os.path.expanduser("~"), "Documents")
default_log_path = os.path.join(user_documents, "NotchRenderLog.txt")
def on_codec_changed(*args):
    try:
        selected_codec = dialog.GetValue("CodecBox").lower()
        is_image_format = selected_codec in IMAGE_CODECS
        dialog.SetValue("IndividualFramesBox", is_image_format)
        print(f"🎚️ Codec changed to '{selected_codec}' — IndividualFrames set to {is_image_format}")
    except Exception as e:
        print(f"⚠️ Error in codec change handler: {e}")

def on_submit(*args):
    try:
        # Log the start of the submission process
        print("✅ Submission started...")

        # Get values from dialog
        scene = dialog.GetValue("SceneFileBox")
        output_folder = dialog.GetValue("OutputFolderBox")
        output_name = dialog.GetValue("OutputNameBox").strip()
        width = dialog.GetValue("WidthBox")
        height = dialog.GetValue("HeightBox")
        individual_frames = dialog.GetValue("IndividualFramesBox")
        start_frame = int(dialog.GetValue("StartFrameBox"))
        end_frame = int(dialog.GetValue("EndFrameBox"))
        quality = dialog.GetValue("QualityBox")     
        bitrate = dialog.GetValue("BitrateBox")           
        job_name = dialog.GetValue("JobNameBox")
        refines = dialog.GetValue("RefinesBox")
        log = dialog.GetValue("LogBox")
        layer = dialog.GetValue("LayerBox")
        fps = dialog.GetValue("FPSBox")
        
        # In your on_submit function, replace:
        allowed_scene_extensions = ['.dfx']  # Allowed Notch file extension

        # With:
        if not validate_file_extension(scene, ALLOWED_SCENE_EXTENSIONS):
            log_message("Validation Error", "⚠️ Invalid scene file type - must be a .notch file")
            return

        # And update the codec validation section:
        if codec not in ALLOWED_OUTPUT_EXTENSIONS:
            log_message("Validation Error", f"⚠️ Invalid codec: {codec}")
            return

        # Ensure output extension matches codec
        output_ext = os.path.splitext(output_name)[1].lower()
        if not output_ext:
            output_name += ALLOWED_OUTPUT_EXTENSIONS[codec][0]  # Use first allowed extension
        elif output_ext not in ALLOWED_OUTPUT_EXTENSIONS[codec]:
            log_message("Validation Error", f"⚠️ Invalid extension for codec {codec}: {output_ext}")
            return

        # Validate scene file
        if not is_safe_path(scene):
            log_message("Validation Error", "⚠️ Invalid scene file path")
            return
            
        allowed_scene_extensions = ['.dfx']  # Add your allowed extensions
        if not validate_file_extension(scene, allowed_scene_extensions):
            log_message("Validation Error", "⚠️ Invalid scene file type")
            return
            
        # Validate output folder
        if not is_safe_path(output_folder):
            log_message("Validation Error", "⚠️ Invalid output folder path")
            return
            
        # Create output folder if it doesn't exist
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            log_message("Error", f"⚠️ Failed to create output folder: {e}")
            return

        # Add resolution validation
        if not validate_resolution(width, height):
            log_message("Validation Error", f"⚠️ Invalid resolution values: {width}x{height}")
            return

        # Add log file validation
        if log and not is_safe_path(log):
            log_message("Validation Error", "⚠️ Invalid log file path")
            return

        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log)
        try:
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
        except Exception as e:
            log_message("Error", f"⚠️ Failed to create log directory: {e}")
            return

        # Sanitize output filename
        sanitized_output_name = sanitize_filename(output_name)
        if sanitized_output_name != output_name:
            print(f"ℹ️ Output filename sanitized: {output_name} → {sanitized_output_name}")
            output_name = sanitized_output_name

        # Validate codec and file extension
        codec = dialog.GetValue("CodecBox")
        allowed_codecs = {
            "notchlc": [".mov"],
            "h264": [".mp4"],
            "h265": [".mp4"],
            "hap": [".mov"],
            "mov": [".mov"],
            "exr": [".exr"],
            "png": [".png"],
            "jpg": [".jpg"],
            "tga": [".tga"],
            "tiff": [".tif"]
        }
        
        if codec not in allowed_codecs:
            log_message("Validation Error", f"Invalid codec: {codec}")
            return

        # Ensure output extension matches codec
        output_ext = os.path.splitext(output_name)[1].lower()
        if not output_ext:
            output_name += allowed_codecs[codec][0]  # Use first allowed extension
        elif output_ext not in allowed_codecs[codec]:
            log_message("Validation Error", f"Invalid extension for codec {codec}: {output_ext}")
            return

        # Rebuild full path
        output_full_path = os.path.join(output_folder, output_name)

        # Frame settings
        frame_range = f"{start_frame}-{end_frame}"
        chunk_size = 1 if individual_frames else end_frame - start_frame + 1

        # Get temp directory
        param_file_path = RepositoryUtils.GetRepositoryFilePath("custom/plugins/NotchCmdRender/NotchCmdRender.param", True)
        custom_temp_dir = ""

        try:
            with open(param_file_path, "r") as f:
                for line in f:
                    if line.strip().startswith("TempDir="):
                        _, val = line.split("=", 1)
                        custom_temp_dir = val.strip()
                        break
        except Exception as e:
            print(f"⚠️ Could not read TempDir from param file: {e}")

        if custom_temp_dir and os.path.isdir(custom_temp_dir):
            temp_dir = custom_temp_dir
            print(f"📂 Using custom TempDir: {temp_dir}")
        else:
            temp_dir = ClientUtils.GetDeadlineTempPath()
            print(f"📁 Using default Deadline temp path: {temp_dir}")

        job_info_filename = os.path.join(temp_dir, "notch_job_info.job")
        plugin_info_filename = os.path.join(temp_dir, "notch_plugin_info.job")

        # Write to job info file
        try:
            with open(job_info_filename, 'w', encoding='utf-8') as job_file:
                job_file.write(f"Plugin=NotchCmdRender\n")
                job_file.write(f"Name={job_name}\n")
                job_file.write(f"Frames={frame_range}\n")
                job_file.write(f"ChunkSize={chunk_size}\n")
        except IOError as e:
            log_message("File Error", f"⚠️ Failed to write job info file: {e}")
            return
        except Exception as e:
            log_message("Unexpected Error", f"⚠️ Failed to create job: {e}")
            return

        # Write to plugin info file
        try:
            with open(plugin_info_filename, 'w', encoding='utf-8') as plugin_file:
                plugin_file.write(f"SceneFile={scene}\n")
                plugin_file.write(f"OutputPath={output_full_path}\n")
                plugin_file.write(f"IndividualFrames={individual_frames}\n")
                plugin_file.write(f"Codec={codec}\n")
                plugin_file.write(f"BitRate={bitrate}\n")
                plugin_file.write(f"Quality={quality}\n")
                plugin_file.write(f"ResX={width}\n")
                plugin_file.write(f"ResY={height}\n")
                plugin_file.write(f"StartFrame={start_frame}\n")
                plugin_file.write(f"EndFrame={end_frame}\n")
                plugin_file.write(f"Refines={refines}\n")
                plugin_file.write(f"LogFile={log}\n")
                plugin_file.write(f"Layer={layer}\n")
                plugin_file.write(f"FPS={fps}\n")
                plugin_file.write(f"OutputFile={output_full_path}\n")
                plugin_file.write(f"TempDirectory={temp_dir}\n")
        except IOError as e:
            log_message("File Error", f"⚠️ Failed to write plugin info file: {e}")
            cleanup_temp_files(job_info_filename, plugin_info_filename)
            return
        except Exception as e:
            log_message("Unexpected Error", f"⚠️ Failed to create plugin info: {e}")
            cleanup_temp_files(job_info_filename, plugin_info_filename)
            return

        # Submit job to Deadline
        arguments = [job_info_filename, plugin_info_filename]
        results = ClientUtils.ExecuteCommandAndGetOutput(arguments)
        print(f"Submission Results: {results}")

        # Cleanup temporary files
        cleanup_success = cleanup_temp_files(job_info_filename, plugin_info_filename)
        if not cleanup_success:
            print("⚠️ Some temporary files could not be cleaned up")

        dialog.CloseDialog()

    except Exception as e:
        log_message("Submission Error", f"❌ Unexpected Error:\n{e}")
        # Try to cleanup even if submission failed
        cleanup_temp_files(job_info_filename, plugin_info_filename)

def on_cancel(*args):
    print("🔙 Cancel pressed")
    dialog.CloseDialog()

def log_message(title, message):
    print(f"{title}: {message}")

def __main__():
    try:
        print("✅ Launching NotchCmdRender submission dialog...")

        # Initialize the dialog
        global dialog
        dialog = DeadlineScriptDialog()
        dialog.SetTitle("Notch NURA Job Submission")
        dialog.AddGrid()

        # Job Name
        dialog.AddControlToGrid("JobNameLabel", "LabelControl", "Job Name:", 0, 0)
        dialog.AddControlToGrid("JobNameBox", "TextControl", "NotchRenderJob", 0, 1)

        # Scene File input
        dialog.AddControlToGrid("SceneFileLabel", "LabelControl", "Scene File:", 1, 0)
        dialog.AddControlToGrid("SceneFileBox", "FileBrowserControl", "", 1, 1)

        # Output Path
        dialog.AddControlToGrid("OutputFolderLabel", "LabelControl", "Output Folder:", 2, 0)
        dialog.AddControlToGrid("OutputFolderBox", "FolderBrowserControl", "", 2, 1)

        dialog.AddControlToGrid("OutputNameLabel", "LabelControl", "Output File Name:", 3, 0)
        dialog.AddControlToGrid("OutputNameBox", "TextControl", "", 3, 1)

        # Append frame toggle
        dialog.AddControlToGrid("IndividualFramesLabel", "LabelControl", "Individual Frames:", 3, 2)
        dialog.AddControlToGrid("IndividualFramesBox", "CheckBoxControl", False, 3, 3)

        # Codec selection
        dialog.AddControlToGrid("CodecLabel", "LabelControl", "Codec Type:", 5, 0)
        codec_control = dialog.AddControlToGrid("CodecBox", "ComboControl", "notchlc", 5, 1)
        dialog.SetItems("CodecBox", ["notchlc", "h264", "h265", "hap", "mov", "exr", "png", "jpg", "tga", "tiff"])

        # Quality and Bitrate
        dialog.AddControlToGrid("QualityLabel", "LabelControl", "Quality:", 5, 2)
        dialog.AddControlToGrid("QualityBox", "TextControl", "", 5, 3)

        dialog.AddControlToGrid("BitrateLabel", "LabelControl", "Bitrate:", 5, 4)
        dialog.AddControlToGrid("BitrateBox", "TextControl", "", 5, 5)

        # Resolution
        dialog.AddControlToGrid("WidthLabel", "LabelControl", "Width:", 6, 0)
        dialog.AddControlToGrid("WidthBox", "TextControl", "1920", 6, 1)

        dialog.AddControlToGrid("HeightLabel", "LabelControl", "Height:", 6, 2)
        dialog.AddControlToGrid("HeightBox", "TextControl", "1080", 6, 3)

        # Frame Range
        dialog.AddControlToGrid("StartFrameLabel", "LabelControl", "Start Frame:", 7, 0)
        dialog.AddControlToGrid("StartFrameBox", "TextControl", "0", 7, 1)

        dialog.AddControlToGrid("EndFrameLabel", "LabelControl", "End Frame:", 7, 2)
        dialog.AddControlToGrid("EndFrameBox", "TextControl", "100", 7, 3)

        # FPS
        dialog.AddControlToGrid("FPSLabel", "LabelControl", "FPS:", 8, 0)
        dialog.AddControlToGrid("FPSBox", "TextControl", "30", 8, 1)

        # Refines
        dialog.AddControlToGrid("RefinesLabel", "LabelControl", "Refines:", 9, 0)
        dialog.AddControlToGrid("RefinesBox", "TextControl", "1", 9, 1)

        # Layer
        dialog.AddControlToGrid("LayerLabel", "LabelControl", "Layer:", 10, 0)
        dialog.AddControlToGrid("LayerBox", "TextControl", "", 10, 1)

        # Log File
        dialog.AddControlToGrid("LogLabel", "LabelControl", "Log File:", 14, 0)
        dialog.AddControlToGrid("LogBox", "TextControl", default_log_path, 14, 1)

        dialog.EndGrid()

        # Submit and Cancel buttons
        dialog.AddGrid()
        submitButton = dialog.AddControlToGrid("SubmitButton", "ButtonControl", "Submit", 0, 0, expand=False)
        cancelButton = dialog.AddControlToGrid("CancelButton", "ButtonControl", "Cancel", 0, 1, expand=False)
        dialog.EndGrid()

        # Connect the handlers
        submitButton.ValueModified.connect(on_submit)
        cancelButton.ValueModified.connect(on_cancel)
        codec_control.ValueModified.connect(on_codec_changed)

        # Show the dialog
        dialog.ShowDialog(False)

    except Exception as e:
        print(f"Error during dialog creation: {e}")

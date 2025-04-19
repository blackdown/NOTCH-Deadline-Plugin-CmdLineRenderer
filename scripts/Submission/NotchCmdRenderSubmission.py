from System import *
from System.IO import *
from Deadline.Scripting import *
from Deadline.Plugins import *
from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog
from Deadline.Scripting import RepositoryUtils, ClientUtils
from Deadline.Events import EventManager

import os
import re
import time
from pathlib import Path

# Original constant definitions
ALLOWED_SCENE_EXTENSIONS = ['.dfx']
ALLOWED_OUTPUT_EXTENSIONS = {
    "notchlc": [".mov"],
    "h264": [".mp4"],
    "h265": [".mp4"],
    "hap": [".mov"],
    "mov": [".mov"],
    "exr": [".exr"],
    "png": [".png"],
    "jpeg": [".jpg", ".jpeg"],
    "tga": [".tga"],
    "tiff": [".tif", ".tiff"]
}

IMAGE_CODECS = {"exr", "png", "jpeg", "tga", "tiff"}

# Default paths
user_documents = os.path.join(os.path.expanduser("~"), "Documents")
default_log_path = os.path.join(user_documents, "NotchRenderLog.txt")

# Add this constant for log file format validation
ALLOWED_LOG_EXTENSIONS = [".txt", ".log"]

def get_temp_directory():
    """Returns a temporary directory path for job files"""
    temp_dir = os.environ.get('TEMP') or os.environ.get('TMP') or os.path.join(os.path.expanduser("~"), "NotchTemp")
    try:
        os.makedirs(temp_dir, exist_ok=True)
        test_file = os.path.join(temp_dir, "write_test")
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
    except (OSError, IOError) as e:
        title = "Temp Directory"
        error_msg = f"Error accessing temp directory: {e}\nUsing fallback directory: {os.getcwd()}"
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return os.getcwd()
    except Exception as e:
        title = "Temp Directory"
        error_msg = f"Unexpected error creating temp directory: {type(e).__name__}: {e}\nUsing fallback directory: {os.getcwd()}"
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return os.getcwd()
    return temp_dir

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
    except IOError as e:
        print(f"⚠️ IOError detected while checking file lock: {e}")
        return True

def check_windows_environment():
    """Verify Windows-specific requirements"""
    try:
        if os.name != 'nt':
            return False
            
        required_dirs = [
            os.environ.get('TEMP'),
            os.environ.get('SystemRoot')
        ]
        
        for required_directory in required_dirs:
            if not required_directory or not os.path.exists(required_directory):
                return False
                
        return True
        
    except (KeyError, FileNotFoundError, OSError) as e:
        print(f"⚠️ Error checking Windows environment: {e}")
        return False

def is_safe_path(path):
    """Validates if a file path is safe to use."""
    try:
        absolute_path = os.path.abspath(normalize_windows_path(path))
        
        unsafe_chars = ['<', '>', '|', '*', '?', '"', ';', '&', '$']
        if any(char in path for char in unsafe_chars):
            title = "Path"
            error_msg = f"Path contains unsafe characters: {path}"
            dialog.ShowMessageBox(error_msg, title, ("Ok",))
            print(f"ERROR: {title}: {error_msg}")
            return False
            
        if '..' in path:
            title = "Path"
            error_msg = f"Path contains suspicious traversal patterns: {path}"
            dialog.ShowMessageBox(error_msg, title, ("Ok",))
            print(f"ERROR: {title}: {error_msg}")
            return False
            
        if len(absolute_path) > 260:
            title = "Path"
            error_msg = f"Path exceeds maximum length ({len(absolute_path)} characters)"
            dialog.ShowMessageBox(error_msg, title, ("Ok",))
            print(f"ERROR: {title}: {error_msg}")
            return False
            
        return True
        
    except Exception as e:
        title = "Path"
        error_msg = f"Path validation error: {str(e)}"
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return False

def validate_resolution():
    width = dialog.GetValue("WidthBox")
    height = dialog.GetValue("HeightBox")
    try:
        w, h = int(width), int(height)
        if w <= 0 or h <= 0 or w > 16384 or h > 16384:
            title = "Resolution"
            error_msg = (
                f"Invalid resolution: {w}x{h}\n\n"
                f"Resolution must be between 1x1 and 16384x16384"
            )
            dialog.ShowMessageBox(error_msg, title, ("Ok",))
            print(f"ERROR: {title}: {error_msg}")
            return False
        return True
    except (ValueError, TypeError):
        title = "Resolution"
        error_msg = "Resolution values must be valid numbers"
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return False

def validate_file_extension(filename, allowed_extensions):
    """Validates that a file has an allowed extension"""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed_extensions:
        # Build a more detailed error message
        error_title = "Invalid File Extension" 
        error_detail = (
            f"The file extension '{ext}' is not supported.\n\n"
            f"Allowed extensions: {', '.join(allowed_extensions)}"
        )
        
        # Use Deadline's built-in dialog system - message body first, then title
        dialog.ShowMessageBox(error_detail, error_title, ("Ok",))
        
        # Log the error
        print(f"ERROR: {error_title}: {error_detail}")
        return False
    return True

def sanitize_filename(filename):
    unsafe_chars = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
    sanitized = unsafe_chars.sub('_', filename)
    
    MAX_FILENAME_LENGTH = 255
    name, ext = os.path.splitext(sanitized)
    if len(sanitized) > MAX_FILENAME_LENGTH:
        sanitized = name[:MAX_FILENAME_LENGTH-len(ext)] + ext
        
    return sanitized

def cleanup_temp_files(job_info_filename, plugin_info_filename):
    files_to_cleanup = [
        (job_info_filename, "job info"),
        (plugin_info_filename, "plugin info")
    ]
    
    cleanup_success = True
    
    for file_path, file_type in files_to_cleanup:
        try:
            if os.path.exists(file_path):
                max_attempts = 5
                for attempt in range(max_attempts):
                    if is_file_locked(file_path):
                        if attempt == max_attempts - 1:
                            title = "File Locked"
                            error_msg = f"File is still locked after {max_attempts} attempts:\n{file_path}"
                            dialog.ShowMessageBox(error_msg, title, ("Ok",))
                            print(f"WARNING: {title}: {error_msg}")
                        time.sleep(1)
                    else:
                        try:
                            os.remove(file_path)
                            print(f"INFO: Cleanup: Cleaned up {file_type} file")
                            break
                        except PermissionError:
                            if attempt == max_attempts - 1:
                                title = "Permission Error"
                                error_msg = f"Failed to remove {file_type} file:\n{file_path}"
                                dialog.ShowMessageBox(error_msg, title, ("Ok",))
                                print(f"ERROR: {title}: {error_msg}")
                                cleanup_success = False
                else:
                    cleanup_success = False
            else:
                print(f"INFO: Cleanup: {file_type} file not found: {file_path}")
        except Exception as e:
            title = "Cleanup Error"
            error_msg = f"Error cleaning up {file_type} file:\n{file_path}\n\nError: {str(e)}"
            dialog.ShowMessageBox(error_msg, title, ("Ok",))
            print(f"ERROR: {title}: {error_msg}")
            cleanup_success = False
    
    return cleanup_success

def on_codec_changed(*args):
    try:
        selected_codec = dialog.GetValue("CodecBox").lower()
        is_image_format = selected_codec in IMAGE_CODECS
        dialog.SetValue("IndividualFramesBox", is_image_format)
        # Only print codec changes, don't show GUI message
        print(f"INFO: Codec Changed: {selected_codec} - Individual Frames: {is_image_format}")
    except Exception as e:
        error_msg = f"Error in codec change handler: {e}"
        dialog.ShowMessageBox(error_msg, "Codec Error", ("Ok",))
        print(f"ERROR: Codec Error: {error_msg}")

def validate_scene_file():
    scene = dialog.GetValue("SceneFileBox")
    if not scene:
        title = "Scene File"
        error_msg = "No scene file selected.\nPlease select a Notch (.dfx) file."
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return False
    if not validate_file_extension(scene, ALLOWED_SCENE_EXTENSIONS):
        return False
    return True

def validate_paths():
    scene = dialog.GetValue("SceneFileBox")
    output_folder = dialog.GetValue("OutputFolderBox")
    
    errors = []
    if not is_safe_path(scene):
        errors.append(f"Invalid scene file path:\n{scene}")
    if not is_safe_path(output_folder):
        errors.append(f"Invalid output folder path:\n{output_folder}")
        
    if errors:
        title = "Path Validation"
        error_msg = "\n\n".join(errors)
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return False
    return True

def validate_log_path():
    log_folder = dialog.GetValue("LogFolderBox")
    log_filename = dialog.GetValue("LogFileNameBox").strip()
    
    if not log_folder or not log_filename:
        # Log is optional, so empty values are fine
        return True
    
    # Validate folder path
    if not is_safe_path(log_folder):
        error_msg = f"Invalid log folder path: {log_folder}"
        dialog.ShowMessageBox(error_msg, "Log Folder Error", ("Ok",))
        print(f"ERROR: Log Folder Error: {error_msg}")
        return False
    
    # Validate filename format
    log_ext = os.path.splitext(log_filename)[1].lower()
    if not log_ext:
        # Add default extension if none provided
        log_filename += ".txt"
    elif log_ext not in ALLOWED_LOG_EXTENSIONS:
        error_msg = (
            f"Invalid log file extension: {log_ext}\n\n"
            f"Allowed extensions: {', '.join(ALLOWED_LOG_EXTENSIONS)}"
        )
        dialog.ShowMessageBox(error_msg, "Log File Error", ("Ok",))
        print(f"ERROR: Log File Error: {error_msg}")
        return False
    
    # Check for unsafe characters in filename
    sanitized_filename = sanitize_filename(log_filename)
    if sanitized_filename != log_filename:
        info_msg = (
            f"The log filename has been sanitized:\n\n"
            f"Original: {log_filename}\n"
            f"Sanitized: {sanitized_filename}"
        )
        dialog.ShowMessageBox(info_msg, "Log Filename Modified", ("Ok",))
        print(f"INFO: Log Filename Modified: {info_msg}")
        dialog.SetValue("LogFileNameBox", sanitized_filename)
    
    return True

def get_full_log_path():
    """Combine log folder and filename to get full log path"""
    log_folder = dialog.GetValue("LogFolderBox")
    log_filename = dialog.GetValue("LogFileNameBox").strip()
    
    if not log_folder or not log_filename:
        return ""
    
    # Ensure filename has an extension
    if not os.path.splitext(log_filename)[1]:
        log_filename += ".txt"
    
    return os.path.join(log_folder, sanitize_filename(log_filename))

def validate_codec():
    try:
        codec = dialog.GetValue("CodecBox")
        if not isinstance(codec, str):
            title = "Codec"
            error_msg = f"Invalid codec type.\nExpected string but got: {type(codec)}"
            dialog.ShowMessageBox(error_msg, title, ("Ok",))
            print(f"ERROR: {title}: {error_msg}")
            return False
        if codec is None or not codec.strip():
            title = "Codec"
            error_msg = "No codec selected.\nPlease select an output codec."
            dialog.ShowMessageBox(error_msg, title, ("Ok",))
            print(f"ERROR: {title}: {error_msg}")
            return False
        if codec.lower() not in ALLOWED_OUTPUT_EXTENSIONS:
            title = "Codec"
            error_msg = (
                f"Unsupported codec: {codec}\n\n"
                f"Supported codecs:\n" + 
                "\n".join([f"- {c}" for c in ALLOWED_OUTPUT_EXTENSIONS.keys()])
            )
            dialog.ShowMessageBox(error_msg, title, ("Ok",))
            print(f"ERROR: {title}: {error_msg}")
            return False
        return True
    except Exception as e:
        title = "Codec"
        error_msg = f"Error validating codec:\n{str(e)}"
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return False

def prepare_output():
    output_folder = dialog.GetValue("OutputFolderBox")
    output_name = dialog.GetValue("OutputNameBox").strip()
    codec = dialog.GetValue("CodecBox")

    if not output_name:
        error_msg = "Please enter an output file name"
        dialog.ShowMessageBox(error_msg, "Output Error", ("Ok",))
        print(f"ERROR: Output Error: {error_msg}")
        return None

    try:
        os.makedirs(output_folder, exist_ok=True)
    except Exception as e:
        error_msg = (
            f"Failed to create output folder:\n{output_folder}\n\n"
            f"Error: {str(e)}"
        )
        dialog.ShowMessageBox(error_msg, "Output Folder Error", ("Ok",))
        print(f"ERROR: Output Folder Error: {error_msg}")
        return None

    sanitized_output_name = sanitize_filename(output_name)
    if sanitized_output_name != output_name:
        info_msg = (
            f"The output filename has been sanitized:\n\n"
            f"Original: {output_name}\n"
            f"Sanitized: {sanitized_output_name}"
        )
        dialog.ShowMessageBox(info_msg, "Output Name Modified", ("Ok",))
        print(f"INFO: Output Name Modified: {info_msg}")
        output_name = sanitized_output_name

    output_ext = os.path.splitext(output_name)[1].lower()
    if not output_ext:
        output_name += ALLOWED_OUTPUT_EXTENSIONS[codec][0]
    elif output_ext not in ALLOWED_OUTPUT_EXTENSIONS[codec]:
        error_msg = (
            f"Invalid file extension for codec {codec}:\n"
            f"Extension: {output_ext}\n\n"
            f"Allowed extensions for {codec}:\n" +
            "\n".join([f"- {ext}" for ext in ALLOWED_OUTPUT_EXTENSIONS[codec]])
        )
        dialog.ShowMessageBox(error_msg, "Output Extension Error", ("Ok",))
        print(f"ERROR: Output Extension Error: {error_msg}")
        return None

    return os.path.join(output_folder, output_name)

def get_pools():
    """Get list of available Deadline pools"""
    try:
        # Start with 'none' as the first pool
        all_pools = ['none']
        # Add any other pools from the repository
        try:
            repo_pools = RepositoryUtils.GetPoolNames()
            if repo_pools:
                # Convert to Python strings and filter out empty or None values
                pool_list = [str(p) for p in repo_pools if p]
                # Add non-'none' pools
                all_pools.extend(p for p in pool_list if p.lower() != 'none')
        except:
            pass
        return all_pools
    except Exception as e:
        print(f"⚠️ Error getting pools: {e}")
        return ['none']

def validate_pool():
    """Validates that a pool is selected"""
    pool = dialog.GetValue("PoolBox")
    # Allow 'none' as a valid pool selection
    return True

def write_job_info(job_info_filename, job_name, frame_range, chunk_size):
    try:
        with open(job_info_filename, 'w', encoding='utf-8') as job_file:
            job_file.write(f"Plugin=NotchCmdRender\n")
            job_file.write(f"Name={job_name}\n")
            job_file.write(f"Frames={frame_range}\n")
            job_file.write(f"ChunkSize={chunk_size}\n")
            # Only write pool if it's not 'none'
            pool = dialog.GetValue("PoolBox")
            if pool and pool.lower() != "none":
                job_file.write(f"Pool={pool}\n")
    except IOError as e:
        title = "Job Info"
        error_msg = f"Failed to write job info file: {e}"
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return False
    except Exception as e:
        title = "Job Info"
        error_msg = f"Failed to create job: {e}"
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return False
    return True

def write_plugin_info(plugin_info_filename, scene, output_full_path, individual_frames, codec, bitrate, quality, width, height, start_frame, end_frame, refines, log, layer, fps, temp_dir):
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
        title = "Plugin Info"
        error_msg = f"Failed to write plugin info file: {e}"
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return False
    except Exception as e:
        title = "Plugin Info"
        error_msg = f"Failed to create plugin info: {e}"
        dialog.ShowMessageBox(error_msg, title, ("Ok",))
        print(f"ERROR: {title}: {error_msg}")
        return False
    return True

def validate_input():
    # Perform all validations and store results
    scene_valid = validate_scene_file()
    paths_valid = validate_paths()
    resolution_valid = validate_resolution()
    log_valid = validate_log_path()
    codec_valid = validate_codec()
    pool_valid = validate_pool()

    # Return True only if all validations pass
    return all([scene_valid, paths_valid, resolution_valid, log_valid, codec_valid, pool_valid])

def show_message(title, message, is_error=False):
    """Display a message in the Deadline Monitor GUI"""
    if is_error:
        # Use the title as a brief error type and put details in message body
        dialog.ShowMessageBox(message, title, ("Ok",))
        print(f"ERROR: {title}: {message}")
    else:
        print(f"{title}: {message}")

def log_message(title, message):
    """Log a message and show in GUI if it's an error"""
    is_error = any(err in title.lower() for err in ["error", "warning", "invalid", "failed"])
    if is_error:
        if "warning" in title.lower():
            print(f"WARNING: {title}: {message}")
        else:
            print(f"ERROR: {title}: {message}")
        # Pass the full message directly to show_message
        show_message(title, message, is_error)
    else:
        print(f"INFO: {title}: {message}")
        show_message(title, message, is_error)

def on_submit(*args):
    job_info_filename = None
    plugin_info_filename = None

    try:
        print("✅ Submission started...")

        if not validate_input():
            return

        output_full_path = prepare_output()
        if not output_full_path:
            return

        scene = dialog.GetValue("SceneFileBox")
        individual_frames = dialog.GetValue("IndividualFramesBox")
        
        try:
            start_frame = int(dialog.GetValue("StartFrameBox"))
            end_frame = int(dialog.GetValue("EndFrameBox"))
            if start_frame > end_frame:
                title = "Frame Range"
                error_msg = (
                    f"Invalid frame range configuration:\n\n"
                    f"Start Frame: {start_frame}\n"
                    f"End Frame: {end_frame}\n\n"
                    "Start frame must be less than or equal to end frame"
                )
                dialog.ShowMessageBox(error_msg, title, ("Ok",))
                print(f"ERROR: {title}: {error_msg}")
                return
        except ValueError:
            title = "Frame Range"
            error_msg = "Frame values must be valid integers.\n\nPlease check Start Frame and End Frame values."
            dialog.ShowMessageBox(error_msg, title, ("Ok",))
            print(f"ERROR: {title}: {error_msg}")
            return
            
        quality = dialog.GetValue("QualityBox").strip()
        bitrate = dialog.GetValue("BitrateBox").strip()
            
        job_name = dialog.GetValue("JobNameBox")
        refines = dialog.GetValue("RefinesBox")
        log = get_full_log_path()  # Use the new function
        layer = dialog.GetValue("LayerBox")
        fps = dialog.GetValue("FPSBox")
        width = dialog.GetValue("WidthBox")
        height = dialog.GetValue("HeightBox")
        codec = dialog.GetValue("CodecBox")

        frame_range = f"{start_frame}-{end_frame}"
        chunk_size = 1 if individual_frames else end_frame - start_frame + 1

        temp_dir = get_temp_directory()

        job_info_filename = os.path.join(temp_dir, "notch_job_info.job")
        plugin_info_filename = os.path.join(temp_dir, "notch_plugin_info.job")

        if not write_job_info(job_info_filename, job_name, frame_range, chunk_size):
            cleanup_temp_files(job_info_filename, plugin_info_filename)
            return

        if not write_plugin_info(plugin_info_filename, scene, output_full_path, individual_frames, codec, bitrate, quality, width, height, start_frame, end_frame, refines, log, layer, fps, temp_dir):
            cleanup_temp_files(job_info_filename, plugin_info_filename)
            return

        arguments = [job_info_filename, plugin_info_filename]
        results = ClientUtils.ExecuteCommandAndGetOutput(arguments)
        print(f"Submission Results: {results}")

        cleanup_success = cleanup_temp_files(job_info_filename, plugin_info_filename)
        if not cleanup_success:
            print("⚠️ Some temporary files could not be cleaned up")

        dialog.CloseDialog()

    except Exception as e:
        error_msg = f"❌ Unexpected Error:\n{e}"
        dialog.ShowMessageBox(error_msg, "Submission Error", ("Ok",))
        print(f"ERROR: Submission Error: {error_msg}")
        cleanup_temp_files(job_info_filename, plugin_info_filename)

def on_cancel(*args):
    print("🔙 Cancel pressed")
    dialog.CloseDialog()

def __main__():
    try:
        print("✅ Launching NotchCmdRender submission dialog...")

        # Initialize the dialog
        global dialog
        dialog = DeadlineScriptDialog()
        dialog.SetTitle("Notch NURA Render")
        dialog.AddGrid()

        # Job Name and Pool Selection on same row
        dialog.AddControlToGrid("JobNameLabel", "LabelControl", "Job Name:", 0, 0)
        dialog.AddControlToGrid("JobNameBox", "TextControl", "NotchRenderJob", 0, 1)
        dialog.AddControlToGrid("PoolLabel", "LabelControl", "Worker Pool:", 0, 2)
        pool_control = dialog.AddControlToGrid("PoolBox", "ComboControl", "none", 0, 3)
        # Set default pool first
        dialog.SetValue("PoolBox", "none")
        # Then set the items list
        try:
            pools = get_pools()
            if pools:
                dialog.SetItems("PoolBox", pools)
        except Exception as e:
            print(f"⚠️ Error setting pool items: {e}")
            # Ensure at least 'none' is available
            dialog.SetItems("PoolBox", ["none"])

        # Scene File input - back to original row number
        dialog.AddControlToGrid("SceneFileLabel", "LabelControl", "Scene File:", 1, 0)
        dialog.AddControlToGrid("SceneFileBox", "FileBrowserControl", "", 1, 1)

        # Output Path - adjusted row numbers
        dialog.AddControlToGrid("OutputFolderLabel", "LabelControl", "Output Folder:", 2, 0)
        dialog.AddControlToGrid("OutputFolderBox", "FolderBrowserControl", "", 2, 1)

        dialog.AddControlToGrid("OutputNameLabel", "LabelControl", "Output File Name:", 3, 0)
        dialog.AddControlToGrid("OutputNameBox", "TextControl", "", 3, 1)

        # Append frame toggle - adjusted row
        dialog.AddControlToGrid("IndividualFramesLabel", "LabelControl", "Individual Frames:", 3, 2)
        dialog.AddControlToGrid("IndividualFramesBox", "CheckBoxControl", False, 3, 3)

        # Codec selection
        dialog.AddControlToGrid("CodecLabel", "LabelControl", "Codec Type:", 4, 0)
        codec_control = dialog.AddControlToGrid("CodecBox", "ComboControl", "notchlc", 4, 1)
        dialog.SetItems("CodecBox", ["notchlc", "h264", "h265", "hap", "mov", "exr", "png", "jpeg", "tga", "tiff"])

        # Quality and Bitrate
        dialog.AddControlToGrid("QualityLabel", "LabelControl", "Quality:", 4, 2)
        dialog.AddControlToGrid("QualityBox", "TextControl", "", 4, 3)

        dialog.AddControlToGrid("BitrateLabel", "LabelControl", "Bitrate:", 4, 4)
        dialog.AddControlToGrid("BitrateBox", "TextControl", "", 4, 5)

        # Resolution
        dialog.AddControlToGrid("WidthLabel", "LabelControl", "Width:", 5, 0)
        dialog.AddControlToGrid("WidthBox", "TextControl", "1920", 5, 1)

        dialog.AddControlToGrid("HeightLabel", "LabelControl", "Height:", 5, 2)
        dialog.AddControlToGrid("HeightBox", "TextControl", "1080", 5, 3)

        # Frame Range
        dialog.AddControlToGrid("StartFrameLabel", "LabelControl", "Start Frame:", 6, 0)
        dialog.AddControlToGrid("StartFrameBox", "TextControl", "0", 6, 1)

        dialog.AddControlToGrid("EndFrameLabel", "LabelControl", "End Frame:", 6, 2)
        dialog.AddControlToGrid("EndFrameBox", "TextControl", "100", 6, 3)

        # FPS
        dialog.AddControlToGrid("FPSLabel", "LabelControl", "FPS:", 7, 0)
        dialog.AddControlToGrid("FPSBox", "TextControl", "30", 7, 1)

        # Refines
        dialog.AddControlToGrid("RefinesLabel", "LabelControl", "Refines:", 8, 0)
        dialog.AddControlToGrid("RefinesBox", "TextControl", "1", 8, 1)

        # Layer
        dialog.AddControlToGrid("LayerLabel", "LabelControl", "Layer:", 9, 0)
        dialog.AddControlToGrid("LayerBox", "TextControl", "", 9, 1)

        # Log File - replaced with folder and name controls
        dialog.AddControlToGrid("LogFolderLabel", "LabelControl", "Log Folder:", 10, 0)
        dialog.AddControlToGrid("LogFolderBox", "FolderBrowserControl", os.path.dirname(default_log_path), 10, 1)

        dialog.AddControlToGrid("LogFileNameLabel", "LabelControl", "Log Filename:", 11, 0)
        dialog.AddControlToGrid("LogFileNameBox", "TextControl", "NotchRenderLog.txt", 11, 1)

        dialog.EndGrid()

        # Submit and Cancel buttons
        dialog.AddGrid()
        submitButton = dialog.AddControlToGrid("SubmitButton", "ButtonControl", "Submit", 0, 0, expand=False)
        cancelButton = dialog.AddControlToGrid("CancelButton", "ButtonControl", "Cancel", 0, 1, expand=False)
        dialog.EndGrid()

        # Connect handlers
        submitButton.ValueModified.connect(on_submit)
        cancelButton.ValueModified.connect(on_cancel)
        codec_control.ValueModified.connect(on_codec_changed)

        # Show the dialog
        dialog.ShowDialog(False)

    except Exception as e:
        print(f"Error during dialog creation: {e}")
from Deadline.Plugins import *
from Deadline.Scripting import RepositoryUtils
import os
import re
import sys
import time
import threading

def GetDeadlinePlugin():
    return NotchCmdRenderPlugin()

class NotchCmdRenderPlugin(DeadlinePlugin):
    def __init__(self):
        super().__init__()
        # Fix the callback registration to use the correct Deadline API format
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument
        # Replace these with the standard Deadline callbacks
        self.PreRenderTasksCallback += self.PreRenderTasks
        self.PostRenderTasksCallback += self.PostRenderTasks
        # Remove problematic stdout/stderr callbacks
        
        # Track progress
        self.current_frame = 0
        self.start_frame = 0
        self.end_frame = 0
        self.total_frames = 0
        self.progress_pattern = re.compile(r"Frame\s+(\d+)")
        self.error_patterns = [
            re.compile(r"Error\s*:(.+)", re.IGNORECASE),
            re.compile(r"Exception\s*:(.+)", re.IGNORECASE),
            re.compile(r"Failed\s+to(.+)", re.IGNORECASE)
        ]
        self.warning_pattern = re.compile(r"Warning\s*:(.+)", re.IGNORECASE)
        self.last_status_message = ""
        
        # Log file tracking
        self.log_file_path = None
        self.log_file_last_position = 0
        self.log_monitor_active = False
        self.log_monitor_thread = None
        self.log_polling_interval = 1.0  # seconds
        self.last_log_check_time = 0
        self.last_log_lines = []

    def LogInfoWithProgress(self, message):
        """Log info message and update progress"""
        self.LogInfo(message)
        self.SetStatusMessage(message)

    def LogErrorWithGUI(self, message):
        """Log error to both GUI and Deadline logging system"""
        self.LogError(message)
        self.SetStatusMessage(f"Error: {message}")

    def LogWarningWithGUI(self, message):
        """Log warning to both GUI and Deadline logging system"""
        self.LogWarning(message)
        self.SetStatusMessage(f"Warning: {message}")

    def FailRender(self, message):
        """Override to provide more detailed error messages"""
        self.LogErrorWithGUI(message)
        super(NotchCmdRenderPlugin, self).FailRender(message)
    
    def PreRenderTasks(self):
        """Called before rendering begins - replaces StartJob"""
        self.log_file_path = self.GetPluginInfoEntryWithDefault("LogFile", "")
        if self.log_file_path:
            self.LogInfo(f"Log file monitoring enabled: {self.log_file_path}")
            # Reset monitor state
            self.log_file_last_position = 0
            self.log_monitor_active = True
            
            # Start the log monitoring thread
            self.log_monitor_thread = threading.Thread(target=self.MonitorLogFile)
            self.log_monitor_thread.daemon = True
            self.log_monitor_thread.start()
        else:
            self.LogInfo("No log file specified, monitoring disabled")
        
        return True
    
    def PostRenderTasks(self):
        """Called after rendering ends - replaces EndJob"""
        # Stop the log monitor thread
        self.log_monitor_active = False
        if self.log_monitor_thread:
            try:
                self.log_monitor_thread.join(timeout=5.0)
            except:
                pass
            self.log_monitor_thread = None
        
        return True
    
    def MonitoredManagedProcessExit(self, name):
        """Called when a monitored process exits"""
        self.LogInfo(f"Process '{name}' has exited")
        return True
    
    def MonitorLogFile(self):
        """Thread function to monitor the log file for changes"""
        self.LogInfo("Log monitoring thread started")
        
        try:
            while self.log_monitor_active:
                try:
                    if os.path.exists(self.log_file_path):
                        self.CheckLogFileForUpdates()
                    time.sleep(self.log_polling_interval)
                except Exception as e:
                    self.LogWarning(f"Error while monitoring log file: {str(e)}")
                    # Don't spam with errors, wait a bit longer
                    time.sleep(5.0)
        except:
            self.LogWarning("Log monitoring thread exited unexpectedly")
        
        self.LogInfo("Log monitoring thread stopped")
    
    def CheckLogFileForUpdates(self):
        """Check if the log file has new content and update status if it does"""
        current_time = time.time()
        
        # Don't check too frequently to avoid performance issues
        if current_time - self.last_log_check_time < self.log_polling_interval:
            return
        
        self.last_log_check_time = current_time
        
        try:
            # Check if file exists and is readable
            if not os.path.exists(self.log_file_path):
                return
                
            file_size = os.path.getsize(self.log_file_path)
            
            # If file got smaller or is empty, reset position
            if file_size < self.log_file_last_position or file_size == 0:
                self.log_file_last_position = 0
                
            # If file hasn't changed, don't read it
            if file_size == self.log_file_last_position:
                return
            
            # Handle different encodings and error cases gracefully    
            encodings_to_try = ['utf-8', 'latin1', 'cp1252']
            success = False
            
            for encoding in encodings_to_try:
                try:
                    # Read new content only
                    with open(self.log_file_path, 'r', encoding=encoding, errors='replace') as log_file:
                        if self.log_file_last_position > 0:
                            log_file.seek(self.log_file_last_position)
                            
                        new_content = log_file.read()
                        self.log_file_last_position = log_file.tell()
                    
                    success = True
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    self.LogWarning(f"Error reading log file with {encoding} encoding: {str(e)}")
            
            if not success or not new_content:
                return
            
            # Process new content for display
            lines = new_content.splitlines()
            if not lines:
                return
                
            # Get the latest few lines (up to 3) to display
            significant_lines = []
            for line in reversed(lines):
                line = line.strip()
                if len(line) > 5:  # Skip very short lines
                    significant_lines.append(line)
                    if len(significant_lines) >= 3:
                        break
                        
            if not significant_lines:
                return
                
            # Update the status with the latest significant lines
            self.last_log_lines = list(reversed(significant_lines))
            status = " | ".join(self.last_log_lines)
            
            # Update progress if Frame info is found
            for line in lines:
                progress_match = self.progress_pattern.search(line)
                if progress_match:
                    try:
                        self.current_frame = int(progress_match.group(1))
                        if self.total_frames > 0:
                            progress = (self.current_frame - self.start_frame + 1) / float(self.total_frames) * 100.0
                            self.SetProgress(min(progress, 100.0))
                    except:
                        pass
            
            # Set status message, but don't override error/warning messages
            if not self.last_status_message or not any(x in self.last_status_message.lower() for x in ["error", "warning"]):
                self.SetStatusMessage(f"Log: {status}")
                
            # Log to Deadline logs as well
            self.LogInfo(f"Log file update: {status}")
                
        except Exception as e:
            self.LogWarning(f"Error reading log file: {str(e)}")

    def InitializeProcess(self):
        # Automatically set SingleFramesOnly if IndividualFrames is checked
        individual_frames = self.GetBooleanPluginInfoEntryWithDefault("IndividualFrames", False)
        self.SingleFramesOnly = individual_frames
        self.LogInfoWithProgress(f"Set SingleFramesOnly to: {self.SingleFramesOnly}")

        # This is correct - keep it as Simple
        self.PluginType = PluginType.Simple
        
        # Enable built-in stdout handling for this job
        self.StdoutHandling = True
        
        # Get frame range for progress tracking
        self.start_frame = self.GetIntegerPluginInfoEntryWithDefault("StartFrame", 0)
        self.end_frame = self.GetIntegerPluginInfoEntryWithDefault("EndFrame", 0)
        self.total_frames = self.end_frame - self.start_frame + 1
        self.current_frame = self.start_frame
        
        # Validate executable
        exec_path = self.GetRenderExecutableCandidate()
        if not os.path.exists(exec_path):
            self.FailRender(
                f"Unable to find Notch Command Line Renderer.\n\n"
                f"Expected location: {exec_path}\n\n"
                "Please ensure Notch is installed correctly and the executable path "
                "is set properly in NotchCmdRender.param"
            )
        self.LogInfoWithProgress(f"Using Render Executable: {exec_path}")

    def GetRenderExecutableCandidate(self):
        program_files = os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles") or "C:\\Program Files"
        self.hardcoded_exec_path = os.path.join(program_files, "Notch 1.0", "NotchRenderNodeCLI.exe")

        param_path = RepositoryUtils.GetRepositoryFilePath("custom/plugins/NotchCmdRender/NotchCmdRender.param", True)
        self.param_exec_path = None
        try:
            with open(param_path, "r") as f:
                for line in f:
                    if line.strip().startswith("RenderExecutable="):
                        _, val = line.split("=", 1)
                        self.param_exec_path = val.strip()
                        break
        except Exception as e:
            self.LogWarningWithGUI(
                f"Could not read NotchCmdRender.param:\n{str(e)}\n\n"
                "Will attempt to use default executable location"
            )

        if self.param_exec_path and os.path.exists(self.param_exec_path):
            return self.param_exec_path
        return self.hardcoded_exec_path

    def RenderExecutable(self):
        try:
            exec_path = self.GetRenderExecutableCandidate()
            return exec_path
        except Exception as e:
            self.FailRender(
                "Failed to get render executable:\n\n"
                f"Error: {str(e)}\n\n"
                "Please check the plugin configuration and Notch installation"
            )

    def RenderArgument(self):
        try:
            self.LogInfoWithProgress("RenderArgument: started")

            # Use job frame or override with current frame for IndividualFrames
            frame = self.GetStartFrame()
            individual_frames = self.GetBooleanPluginInfoEntryWithDefault("IndividualFrames", False)

            if individual_frames:
                start = end = frame
                self.LogInfoWithProgress(f"Individual frame mode: rendering only frame {frame}")
            else:
                start = self.GetIntegerPluginInfoEntryWithDefault("StartFrame", frame)
                end = self.GetIntegerPluginInfoEntryWithDefault("EndFrame", frame)
                self.LogInfoWithProgress(f"Rendering full frame range: {start} to {end}")

            args = []

            def quote(val):
                return f'"{val}"' if val and not val.startswith('"') else val

            def opt(key, flag, cast=str):
                value = self.GetPluginInfoEntryWithDefault(key, "")
                self.LogInfoWithProgress(f"{key} = '{value}'")
                if value != "":
                    try:
                        args.extend([flag, quote(str(cast(value)))])
                        self.LogInfoWithProgress(f"Added: {flag} {value}")
                    except Exception as e:
                        self.LogWarningWithGUI(
                            f"Skipped parameter {key}:\n"
                            f"Value: {value}\n"
                            f"Error: {str(e)}"
                        )

            scene = self.GetPluginInfoEntryWithDefault("SceneFile", "")
            output = self.GetPluginInfoEntryWithDefault("OutputPath", "")

            if not scene:
                self.FailRender(
                    "No scene file specified.\n\n"
                    "Please select a valid Notch (.dfx) file"
                )
            if not output:
                self.FailRender(
                    "No output path specified.\n\n"
                    "Please specify an output file path"
                )

            # Append frame number to filename for individual frames
            if individual_frames:
                base, ext = os.path.splitext(output)
                output = f"{base}_{frame:04d}{ext}"

            # Add required parameters first
            args.extend([
                "-document", quote(scene),
                "-out", quote(output),
                "-startframe", str(start),
                "-endframe", str(end)
            ])

            # Optional params with validation
            try:
                opt("Codec", "-codec", str)
            except Exception as e:
                self.FailRender(f"Invalid codec parameter:\n{str(e)}")

            try:
                opt("ResX", "-width", int)
                opt("ResY", "-height", int)
            except Exception as e:
                self.FailRender(
                    f"Invalid resolution parameters:\n\n"
                    f"Error: {str(e)}\n\n"
                    "Width and Height must be valid numbers"
                )

            # Still image flag — use explicit -still rather than adjusting frame range
            codec_val = self.GetPluginInfoEntryWithDefault("Codec", "").lower()
            still_image_codecs = {"jpeg", "png", "tga", "exr", "tif"}
            if codec_val in still_image_codecs:
                args.append("-still")
                self.LogInfoWithProgress(f"Still image codec detected ({codec_val}): added -still flag")

            # Remaining optional params
            opt("FPS", "-fps", float)
            opt("Quality", "-quality", int)
            opt("BitRate", "-bitrate", int)
            opt("LogFile", "-logfile", str)
            opt("Refines", "-refines", int)
            opt("Layer", "-layer", int)
            opt("LayerName", "-layername", str)
            opt("GPU", "-gpu", str)
            opt("ColourSpace", "-colourspace", str)
            opt("AOV", "-aov", str)

            extra = self.GetPluginInfoEntryWithDefault("ExtraArgs", "").strip()
            if extra:
                args.extend(extra.split())
                self.LogInfoWithProgress(f"ExtraArgs: {extra}")

            final_args = " ".join(args)
            self.LogInfoWithProgress("Final Render Command:")
            self.LogInfoWithProgress(final_args)
            return final_args
            
        except Exception as e:
            self.FailRender(
                "Failed to build render command:\n\n"
                f"Error: {str(e)}\n\n"
                "Please check all parameters and try again"
            )

    def ProcessStdoutLine(self, line):
        """Process stdout from NotchCmdLineRender - this is the standard Deadline method name"""
        line = line.strip()
        
        if not line:
            return
            
        # Check if this is a progress update
        progress_match = self.progress_pattern.search(line)
        if progress_match:
            try:
                self.current_frame = int(progress_match.group(1))
                if self.total_frames > 0:
                    progress = (self.current_frame - self.start_frame + 1) / float(self.total_frames) * 100.0
                    self.SetProgress(min(progress, 100.0))
                    status_msg = f"Rendering frame {self.current_frame} of {self.end_frame} ({progress:.1f}%)"
                    self.SetStatusMessage(status_msg)
                    self.last_status_message = status_msg
                self.LogInfo(f"Notch: {line}")
                return
            except Exception as e:
                self.LogWarning(f"Failed to parse progress: {e} from line: {line}")
        
        # Look for other important info, errors, warnings
        for pattern in self.error_patterns:
            error_match = pattern.search(line)
            if error_match:
                error_msg = error_match.group(1).strip() if error_match.group(1) else line
                self.LogErrorWithGUI(f"Notch Error: {error_msg}")
                return
                
        warning_match = self.warning_pattern.search(line)
        if warning_match:
            warning_msg = warning_match.group(1).strip() if warning_match.group(1) else line
            self.LogWarningWithGUI(f"Notch Warning: {warning_msg}")
            return
            
        # For other output, just log normally and update status
        if len(line) > 10:  # Skip very short lines
            self.SetStatusMessage(f"Notch: {line}")
            self.last_status_message = f"Notch: {line}"
        
        self.LogInfo(f"Notch: {line}")

    def ProcessStderrLine(self, line):
        """Process stderr from NotchCmdLineRender - this is the standard Deadline method name"""
        line = line.strip()
        
        if not line:
            return
            
        self.LogWarningWithGUI(f"Notch stderr: {line}")
        self.SetStatusMessage(f"WARNING: {line}")
        self.last_status_message = f"WARNING: {line}"

def CleanupDeadlinePlugin(plugin):
    """Clean up any resources used by the plugin"""
    # Make sure to stop the log monitoring thread
    plugin.log_monitor_active = False
    if hasattr(plugin, 'log_monitor_thread') and plugin.log_monitor_thread:
        try:
            plugin.log_monitor_thread.join(timeout=2.0)
        except:
            pass
    plugin.LogInfoWithProgress("NotchCmdRender cleanup complete.")

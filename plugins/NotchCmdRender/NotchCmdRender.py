from Deadline.Plugins import *
from Deadline.Scripting import RepositoryUtils
import os

def GetDeadlinePlugin():
    return NotchCmdRenderPlugin()

class NotchCmdRenderPlugin(DeadlinePlugin):
    def __init__(self):
        super().__init__()
        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderExecutableCallback += self.RenderExecutable
        self.RenderArgumentCallback += self.RenderArgument

    def InitializeProcess(self):
        # Automatically set SingleFramesOnly if IndividualFrames is checked
        individual_frames = self.GetBooleanPluginInfoEntryWithDefault("IndividualFrames", False)
        self.SingleFramesOnly = individual_frames
        self.LogInfo(f"🧩 Set SingleFramesOnly to: {self.SingleFramesOnly}")

        self.PluginType = PluginType.Simple
        self.StdoutHandling = True

        # Validate executable
        exec_path = self.GetRenderExecutableCandidate()
        if not os.path.exists(exec_path):
            raise RuntimeError(f"❌ Render executable not found: {exec_path}")
        self.LogInfo(f"✅ Using Render Executable: {exec_path}")

    def GetRenderExecutableCandidate(self):
        program_files = os.environ.get("ProgramW6432") or os.environ.get("ProgramFiles") or "C:\\Program Files"
        self.hardcoded_exec_path = os.path.join(program_files, "Notch 1.0", "NotchCmdLineRender.exe")

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
            self.LogWarning(f"Could not read NotchCmdRender.param: {e}")

        if self.param_exec_path and os.path.exists(self.param_exec_path):
            return self.param_exec_path
        return self.hardcoded_exec_path

    def RenderExecutable(self):
        exec_path = self.GetRenderExecutableCandidate()
        return exec_path

    def RenderArgument(self):
        self.LogInfo("RenderArgument: started")

        # Use job frame or override with current frame for IndividualFrames
        frame = self.GetStartFrame()
        individual_frames = self.GetBooleanPluginInfoEntryWithDefault("IndividualFrames", False)

        if individual_frames:
            start = end = frame
            self.LogInfo(f"🎯 Individual frame mode: rendering only frame {frame}")
        else:
            start = self.GetIntegerPluginInfoEntryWithDefault("StartFrame", frame)
            end = self.GetIntegerPluginInfoEntryWithDefault("EndFrame", frame)
            self.LogInfo(f"🎞️ Rendering full frame range: {start} to {end}")

        args = []

        def quote(val):
            return f'"{val}"' if val and not val.startswith('"') else val

        def opt(key, flag, cast=str):
            value = self.GetPluginInfoEntryWithDefault(key, "")
            self.LogInfo(f"🔧 {key} = '{value}'")
            if value != "":
                try:
                    args.extend([flag, quote(str(cast(value)))])
                    self.LogInfo(f"✅ Added: {flag} {value}")
                except Exception as e:
                    self.LogWarning(f"⚠️ Skipped {key}: {e}")

        scene = self.GetPluginInfoEntryWithDefault("SceneFile", "")
        output = self.GetPluginInfoEntryWithDefault("OutputPath", "")

        # Append frame number to filename for individual frames
        if individual_frames:
            base, ext = os.path.splitext(output)
            output = f"{base}_{frame:04d}{ext}"

        # Add required parameters first
        args.extend([
            "-document", quote(scene),
            "-out", quote(output),
            "-startFrame", str(start),
            "-endFrame", str(end)
        ])

        # Optional params
        opt("Codec", "-Codec", str)
        opt("ResX", "-Width", int)
        opt("ResY", "-Height", int)
        opt("FPS", "-fps", float)
        opt("Quality", "-quality", int)
        opt("BitRate", "-bitrate", int)
        opt("LogFile", "-logfile", str)
        opt("Refines", "-refines", int)
        opt("Layer", "-layer", int)

        extra = self.GetPluginInfoEntryWithDefault("ExtraArgs", "").strip()
        if extra:
            args.extend(extra.split())
            self.LogInfo(f"🧩 ExtraArgs: {extra}")

        final_args = " ".join(args)
        self.LogInfo("🚀 Final Render Command:")
        self.LogInfo(final_args)
        return final_args

def CleanupDeadlinePlugin(plugin):
    plugin.LogInfo("🧼 NotchCmdRender cleanup complete.")

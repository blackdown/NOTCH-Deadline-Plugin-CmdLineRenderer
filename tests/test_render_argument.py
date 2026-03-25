"""
Unit tests for NotchCmdRender.RenderArgument()

Mocks the Deadline plugin base class so these can run on any machine
without Deadline, Notch, or Windows installed.

Run with:  python3 tests/test_render_argument.py
"""

import sys
import os
import shlex

# ---------------------------------------------------------------------------
# Minimal Deadline mock
# ---------------------------------------------------------------------------

class PluginType:
    Simple = "Simple"


class DeadlinePlugin:
    def __init__(self):
        self.InitializeProcessCallback = _Callback()
        self.RenderExecutableCallback  = _Callback()
        self.RenderArgumentCallback    = _Callback()
        self.PreRenderTasksCallback    = _Callback()
        self.PostRenderTasksCallback   = _Callback()
        self.SingleFramesOnly = False
        self.StdoutHandling   = False
        self.PluginType       = PluginType.Simple
        self._info  = {}
        self._frame = 0
        self._logs  = []

    def GetPluginInfoEntryWithDefault(self, key, default):
        return self._info.get(key, default)

    def GetBooleanPluginInfoEntryWithDefault(self, key, default):
        v = self._info.get(key, default)
        if isinstance(v, bool):
            return v
        return str(v).lower() in ("true", "1", "yes")

    def GetIntegerPluginInfoEntryWithDefault(self, key, default):
        return int(self._info.get(key, default))

    def GetStartFrame(self):
        return self._frame

    def LogInfo(self, msg):    self._logs.append(("INFO",    msg))
    def LogWarning(self, msg): self._logs.append(("WARNING", msg))
    def LogError(self, msg):   self._logs.append(("ERROR",   msg))
    def SetStatusMessage(self, msg): pass
    def SetProgress(self, p):        pass

    def FailRender(self, msg):
        raise RuntimeError(f"FailRender: {msg}")


class _Callback:
    def __iadd__(self, fn):
        return self


class RepositoryUtils:
    @staticmethod
    def GetRepositoryFilePath(p, b):
        return "/nonexistent/path"


def _install_mocks():
    sys.modules["Deadline"]           = type(sys)("Deadline")
    sys.modules["Deadline.Plugins"]   = type(sys)("Deadline.Plugins")
    sys.modules["Deadline.Plugins"].DeadlinePlugin = DeadlinePlugin
    sys.modules["Deadline.Plugins"].PluginType     = PluginType
    sys.modules["Deadline.Scripting"] = type(sys)("Deadline.Scripting")
    sys.modules["Deadline.Scripting"].RepositoryUtils = RepositoryUtils


def _load_plugin():
    _install_mocks()
    src_path = os.path.join(
        os.path.dirname(__file__),
        "..", "plugins", "NotchCmdRender", "NotchCmdRender.py"
    )
    ns = {}
    exec(open(src_path).read(), ns)
    return ns["NotchCmdRenderPlugin"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NotchCmdRenderPlugin = _load_plugin()

VIDEO_CODECS = ("notchlc", "h264", "h265", "hap", "hapa", "hapq")
IMAGE_CODECS = ("jpeg", "png", "tga", "exr", "tif")


def _make_plugin(info, frame=0):
    p = NotchCmdRenderPlugin()
    p._info  = info
    p._frame = frame
    return p


def _base_info(**overrides):
    defaults = {
        "SceneFile":      "C:/scene.dfx",
        "OutputPath":     "C:/out/render.mov",
        "IndividualFrames": False,
        "StartFrame":     0,
        "EndFrame":       100,
        "Codec":          "notchlc",
        "ResX":           "1920",
        "ResY":           "1080",
        "FPS":            "30",
        "Refines":        "1",
        "BitRate":        "",
        "Quality":        "",
        "LogFile":        "",
        "Layer":          "",
        "LayerName":      "",
        "GPU":            "",
        "ColourSpace":    "",
        "AOV":            "",
        "ExtraArgs":      "",
    }
    defaults.update(overrides)
    return defaults


def _parse_args(arg_string):
    """Return dict of {flag: value_or_True} from a rendered arg string."""
    tokens = shlex.split(arg_string)
    result = {}
    i = 0
    while i < len(tokens):
        if tokens[i].startswith("-"):
            flag = tokens[i]
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                result[flag] = tokens[i + 1]
                i += 2
            else:
                result[flag] = True
                i += 1
        else:
            i += 1
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

PASS = 0
FAIL = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}{' — ' + detail if detail else ''}")
        FAIL += 1


def test_required_flags_and_casing():
    """All required flags present with correct lowercase casing."""
    p    = _make_plugin(_base_info())
    args = _parse_args(p.RenderArgument())
    check("has -document",   "-document"   in args)
    check("has -out",        "-out"        in args)
    check("has -startframe", "-startframe" in args, "old: -startFrame")
    check("has -endframe",   "-endframe"   in args, "old: -endFrame")
    check("has -codec",      "-codec"      in args, "old: -Codec")
    check("has -width",      "-width"      in args, "old: -Width")
    check("has -height",     "-height"     in args, "old: -Height")
    check("startframe=0",    args.get("-startframe") == "0")
    check("endframe=100",    args.get("-endframe")   == "100")


def test_video_codec_no_still():
    """Video codecs must not receive the -still flag."""
    for codec in VIDEO_CODECS:
        p    = _make_plugin(_base_info(Codec=codec))
        args = _parse_args(p.RenderArgument())
        check(f"{codec}: no -still", "-still" not in args)


def test_image_codecs_get_still():
    """Image codecs must receive the -still flag."""
    for codec in IMAGE_CODECS:
        output_exts = {"jpeg": ".jpg", "png": ".png", "tga": ".tga",
                       "exr": ".exr", "tif": ".tif"}
        p = _make_plugin(_base_info(
            Codec=codec,
            OutputPath=f"C:/out/frame{output_exts[codec]}",
            IndividualFrames=True,
            StartFrame=5, EndFrame=5,
        ), frame=5)
        args = _parse_args(p.RenderArgument())
        check(f"{codec}: has -still", "-still" in args)


def test_still_image_endframe_not_bumped():
    """endframe should stay equal to startframe for still images (no +1 hack)."""
    p    = _make_plugin(_base_info(
        Codec="png", OutputPath="C:/out/frame.png",
        IndividualFrames=True, StartFrame=10, EndFrame=10,
    ), frame=10)
    args = _parse_args(p.RenderArgument())
    check("endframe not bumped to 11", args.get("-endframe") == "10",
          "old code bumped still-image endframe by 1")


def test_individual_frames_appends_number():
    """Individual frames mode appends zero-padded frame number to output path."""
    p    = _make_plugin(_base_info(
        Codec="png", OutputPath="C:/out/frame.png",
        IndividualFrames=True, StartFrame=10, EndFrame=10,
    ), frame=10)
    args = _parse_args(p.RenderArgument())
    check("frame num in output", "_0010" in args.get("-out", ""))


def test_new_optional_flags():
    """New flags (-layername, -gpu, -colourspace, -aov) are passed through."""
    p = _make_plugin(_base_info(
        LayerName="MyLayer",
        GPU="NVIDIA GeForce RTX 4090",
        ColourSpace="acescg",
        AOV="depth",
    ))
    args = _parse_args(p.RenderArgument())
    check("has -layername",        "-layername"   in args)
    check("layername=MyLayer",     args.get("-layername")   == "MyLayer")
    check("has -gpu",              "-gpu"         in args)
    check("has -colourspace",      "-colourspace" in args)
    check("colourspace=acescg",    args.get("-colourspace") == "acescg")
    check("has -aov",              "-aov"         in args)
    check("aov=depth",             args.get("-aov")         == "depth")


def test_empty_optional_flags_omitted():
    """Empty optional values should not appear in the argument string."""
    p    = _make_plugin(_base_info(LayerName="", GPU="", ColourSpace="", AOV=""))
    args = _parse_args(p.RenderArgument())
    check("no -layername when empty", "-layername"   not in args)
    check("no -gpu when empty",       "-gpu"         not in args)
    check("no -colourspace when empty", "-colourspace" not in args)
    check("no -aov when empty",       "-aov"         not in args)


def test_exr_quality_passed():
    """EXR quality value is forwarded via -quality."""
    p    = _make_plugin(_base_info(Codec="exr", OutputPath="C:/out/f.exr",
                                   IndividualFrames=True, Quality="3"))
    args = _parse_args(p.RenderArgument())
    check("exr: has -quality",  "-quality" in args)
    check("exr: quality=3",     args.get("-quality") == "3")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_required_flags_and_casing,
        test_video_codec_no_still,
        test_image_codecs_get_still,
        test_still_image_endframe_not_bumped,
        test_individual_frames_appends_number,
        test_new_optional_flags,
        test_empty_optional_flags_omitted,
        test_exr_quality_passed,
    ]

    for test in tests:
        print(f"\n{test.__name__}")
        test()

    print(f"\nResults: {PASS} passed, {FAIL} failed")
    sys.exit(0 if FAIL == 0 else 1)

# -*- coding: utf-8 -*-
"""打包链路的测试：图形界面在冻结态怎么跑、构建脚本有没有漏东西。

这些不是功能测试，是**把踩过的坑钉成断言**：

  · 核心编译成 `.pyd` 之后，PyInstaller 在它里面一个 import 都看不见 —— 第一次打
    出来的包 `--version` 就报 `No module named 'shlex'`。
  · 图形界面是 runpy 从数据文件里跑的，漏了 `--add-data` 时 `--version` /
    `--status` 全绿，只有敲 `--gui` 才炸。
  · 冻结态没有解释器可拉，`build_cmd` 必须把「自己」当命令行，而不是去找 .py。
"""
import importlib.util
import os
import sys
import types

import pytest

from conftest import CORE_PATH, GUI_PATH, ROOT

BUILD_PATH = os.path.join(ROOT, "tools", "build_exe.py")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "build.yml")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def build():
    return load(BUILD_PATH, "pojia_build_exe")


# --------------------------------------------------------------- 构建脚本

def test_scan_imports_sees_function_level_imports(build):
    """`tkinter` / `winreg` 都是写在函数体里的延迟导入，也必须被扫出来。

    编译成扩展模块之后，这些 import 在包内没有任何痕迹 —— 漏一个，用户点开
    「选择目录」就 AttributeError / ModuleNotFoundError。
    """
    names = build.scan_imports(CORE_PATH)
    for mod in ("shlex", "tkinter", "winreg", "urllib.request", "tomllib"):
        assert mod in names, "没扫到 %s" % mod


def test_hidden_imports_are_importable_here(build):
    """hidden-import 只能是本平台真的有的模块（winreg / msvcrt 在 Linux 上不存在）。"""
    hid = build.hidden_imports(CORE_PATH, GUI_PATH)
    assert "os" in hid and "http.server" in hid
    for m in hid:
        assert build.importable(m), "塞了个本平台没有的模块：%s" % m
    if os.name != "nt":
        assert "winreg" not in hid and "msvcrt" not in hid


def test_gui_imports_are_covered(build):
    """图形界面的 import 必须单独扫一遍 —— 它不在入口脚本里。"""
    hid = build.hidden_imports(GUI_PATH)
    for mod in ("http.server", "secrets", "socket", "threading", "webbrowser"):
        assert mod in hid, "图形界面用到的 %s 没进包" % mod


def test_build_script_ships_gui_as_data(build):
    """`--add-data` 那一条是 GUI 能不能进包的唯一依据，而且分隔符必须走 os.pathsep
    （Windows `;`、POSIX `:`），写死一个分平台就炸。"""
    with open(BUILD_PATH, encoding="utf-8") as f:
        src = f.read()
    assert "os.pathsep" in src
    assert "GUI" in src and "破甲GUI.py" in src
    assert os.path.isfile(build.GUI)


def test_workflow_calls_the_driver_and_smokes_gui():
    """CI 必须走 tools/build_exe.py，并且真的把界面拉起来点一次。"""
    with open(WORKFLOW, encoding="utf-8") as f:
        yml = f.read()
    assert "tools/build_exe.py" in yml
    assert "tools/gui_smoke.py" in yml
    assert "CYTHON_VERSION" in yml


# --------------------------------------------------------------- 图形界面

def test_build_cmd_source_mode(gui):
    cmd = gui.build_cmd("apply", ["wb"])
    assert cmd[1:3] == ["-u", gui.CORE]
    assert cmd[-3:] == ["--apply", "--yes", "--target"] or "--apply" in cmd
    assert cmd[-2:] == ["--target", "wb"]


def test_build_cmd_frozen_uses_self(gui, monkeypatch):
    """冻结态：包里没有 .py，命令行就是 exe 自己。"""
    monkeypatch.setattr(gui, "FROZEN", True)
    monkeypatch.setattr(gui, "CORE", "")
    monkeypatch.setattr(gui, "sys", types.SimpleNamespace(executable="/opt/pojia-ce"))
    assert gui.build_cmd("revert", ["dsh"]) == [
        "/opt/pojia-ce", "--revert", "--yes", "--target", "dsh"]
    assert gui.build_cmd("check", []) == ["/opt/pojia-ce", "--check"]


# --------------------------------------------------------------- 界面选项

def test_build_cmd_passes_dsh_options(gui, monkeypatch):
    """DSH 的两个可选项要真的落到命令行上 —— 界面上选了不生效是最坏的一种。"""
    monkeypatch.setattr(gui, "IS_WIN", True)
    cmd = gui.build_cmd("apply", ["dsh"], "preset", True)
    assert "--dsh-mode" in cmd and cmd[cmd.index("--dsh-mode") + 1] == "preset"
    assert "--git-bash" in cmd
    assert "--apply" in cmd and "--yes" in cmd


def test_build_cmd_omits_dsh_options_without_dsh(gui, monkeypatch):
    """没勾 DSH 就别传 —— 传了核心会照收，但那是噪声，也容易让人以为生效了。"""
    monkeypatch.setattr(gui, "IS_WIN", True)
    cmd = gui.build_cmd("apply", ["wb", "cursor"], "preset", True)
    assert "--dsh-mode" not in cmd and "--git-bash" not in cmd


def test_build_cmd_omits_dsh_options_on_revert(gui, monkeypatch):
    """还原走备份，跟这两个开关无关；预演要传（核心在 dry-run 分支只探测不下载）。"""
    monkeypatch.setattr(gui, "IS_WIN", True)
    assert "--dsh-mode" not in gui.build_cmd("revert", ["dsh"], "preset", True)
    assert "--git-bash" in gui.build_cmd("dryrun", ["dsh"], "inject", True)


def test_build_cmd_git_bash_is_windows_only(gui, monkeypatch):
    """非 Windows 上核心没有 Git Bash 那条路，别把开关传过去。"""
    monkeypatch.setattr(gui, "IS_WIN", False)
    cmd = gui.build_cmd("apply", ["dsh"], "preset", True)
    assert "--git-bash" not in cmd
    assert cmd[cmd.index("--dsh-mode") + 1] == "preset"


def test_pick_options_whitelists_mode(gui):
    """接口不假设调用方是自己那页：模式必须落在白名单里，开关一律布尔化。"""
    assert gui.pick_options({"dsh_mode": "preset", "git_bash": 1}) == ("preset", True)
    assert gui.pick_options({"dsh_mode": "preset", "git_bash": 0}) == ("preset", False)
    assert gui.pick_options({"dsh_mode": "../etc/passwd"}) == ("inject", False)
    assert gui.pick_options({}) == ("inject", False)
    assert gui.pick_options(None) == ("inject", False)


def test_render_page_fills_every_placeholder(gui):
    """占位符漏一个，页面上就会直接显示 `__TOKEN__` 这种东西（或者更糟：没 token）。"""
    page = gui.render_page()
    for left in ("__VERSION__", "__TOKEN__", "__TARGETS__", "__ACTIONS__",
                 "__ISWIN__", "__REPO__", "__REPO_NAME__"):
        assert left not in page, "占位符没替换：%s" % left
    assert gui.TOKEN in page
    assert gui.REPO_URL in page
    assert gui.REPO_NAME in page


def test_modal_panel_class_is_namespaced(gui):
    """弹窗面板不能和清单里的勾选框共用 `.box`。

    勾选框的 `.box` 原本是条裸规则（13px 方框）。弹窗面板叫 `.box` 的时候，那条
    规则先命中它 —— `.modal .box` 只覆盖了 width，没覆盖 height，于是整个卡片被压成
    13px 高，白底只剩标题那一条，正文和按钮全漏到遮罩上。这不是样式没生效，是两个
    语义撞了名。
    """
    page = gui.render_page()
    assert ".modal .panel{" in page, "弹窗面板的类名被改了？"
    assert '<div class="panel">' in page
    # 不允许再出现无作用域的 `.box{}` 规则
    assert "\n  .box{" not in page, "又出现裸 .box 规则了，换个人用 .box 就会再塌一次"


def test_core_version_frozen_asks_self(gui, monkeypatch):
    """冻结态读不到源码，改问 `exe --version`。"""
    monkeypatch.setattr(gui, "FROZEN", True)
    monkeypatch.setattr(gui, "_VER_CACHE", [])
    monkeypatch.setattr(gui, "sys", types.SimpleNamespace(executable="/opt/pojia-ce"))
    seen = {}

    class R:
        stdout = "破甲一键通 8.51-CE\n".encode("utf-8")

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return R()

    monkeypatch.setattr(gui, "subprocess", types.SimpleNamespace(
        run=fake_run, CREATE_NO_WINDOW=0, PIPE=-1, STDOUT=-2, SubprocessError=Exception))
    assert gui.core_version() == "8.51-CE"
    assert seen["cmd"] == ["/opt/pojia-ce", "--version"]
    # 第二次要命中缓存，不能再起进程
    assert gui.core_version() == "8.51-CE"
    assert seen["cmd"] == ["/opt/pojia-ce", "--version"]


def test_core_version_source_mode(gui, core):
    assert gui.core_version() == core.VER_TAG


# --------------------------------------------------------------- 核心侧

def test_gui_source_path_prefers_meipass(core, tmp_path, monkeypatch):
    """冻结态优先用包里那份（sys._MEIPASS），找不到才回落到脚本同目录。"""
    fake = tmp_path / "破甲GUI.py"
    fake.write_text("# packed\n", encoding="utf-8")
    monkeypatch.setattr(core.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert core._gui_source_path() == str(fake)

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(core.sys, "_MEIPASS", str(empty), raising=False)
    assert core._gui_source_path() == os.path.join(core.HERE, "破甲GUI.py")


def test_launch_gui_frozen_runs_in_process(core, tmp_path, monkeypatch):
    """冻结态用 runpy 在**当前进程**里跑，而不是再拉一个 exe。

    这里真的跑一个假 GUI：它往文件里写一行字，跑完断言这行字在 —— 证明 runpy
    那条路是通的（起第二个进程会解两次包，纯属白等）。
    """
    marker = tmp_path / "ran.txt"
    script = tmp_path / "破甲GUI.py"
    script.write_text(
        "with open(%r, 'w', encoding='utf-8') as f:\n    f.write('ok')\n" % str(marker),
        encoding="utf-8")
    monkeypatch.setattr(core, "_gui_source_path", lambda: str(script))
    monkeypatch.setattr(core.sys, "frozen", True, raising=False)
    core._launch_gui()
    assert marker.read_text(encoding="utf-8") == "ok"


def test_launch_gui_missing_file_is_harmless(core, monkeypatch):
    monkeypatch.setattr(core, "_gui_source_path", lambda: "")
    assert core._launch_gui() is False      # 只打印提示，不抛，并且报告没起来


def test_default_gui_only_for_frozen_bare_invocation(core, args, monkeypatch):
    """双击打包版（零参数）默认开界面；源码态和带参数的都还是命令行。

    打包版的使用者大多不是命令行用户，双击先看到一屏 ASCII 菜单是反的。
    """
    monkeypatch.setattr(core.sys, "frozen", True, raising=False)
    monkeypatch.setattr(core.sys, "argv", ["pojia-ce.exe"])
    assert core._default_to_gui(args) is True

    # 带任何参数就不抢：--status / --apply 这些是脚本和守护任务在调
    monkeypatch.setattr(core.sys, "argv", ["pojia-ce.exe", "--status"])
    assert core._default_to_gui(args) is False

    # 显式要菜单
    monkeypatch.setattr(core.sys, "argv", ["pojia-ce.exe"])
    assert core._default_to_gui(type("A", (), {"menu": True})()) is False

    # 源码态不动：python 破甲一键通.py 还是交互菜单
    monkeypatch.setattr(core.sys, "frozen", False, raising=False)
    assert core._default_to_gui(args) is False


def test_gui_main_opens_browser_unless_told_not_to(gui, monkeypatch):
    """打包版双击进来必须自动开浏览器 —— 否则用户只看到一个黑窗口。

    `--no-open`（源码态）和 `POJIA_GUI_NO_OPEN=1`（打包态没地方塞参数）都能关。
    """
    opened = []
    timers = []

    class FakeTimer:
        def __init__(self, delay, fn):
            self.fn = fn
            timers.append(self)

        def start(self):
            pass

    monkeypatch.setattr(gui, "ThreadingHTTPServer", _FakeServer)
    monkeypatch.setattr(gui, "threading", types.SimpleNamespace(Timer=FakeTimer))
    monkeypatch.setattr(gui, "webbrowser",
                        types.SimpleNamespace(open=lambda u: opened.append(u)))
    monkeypatch.setattr(gui.sys, "argv", ["pojia-ce.exe"])
    monkeypatch.delenv("POJIA_GUI_NO_OPEN", raising=False)
    monkeypatch.setattr(gui, "FROZEN", True)
    monkeypatch.setattr(gui, "core_version", lambda: "8.53-CE")

    assert gui.main() == 0
    assert len(timers) == 1
    timers[0].fn()                       # 模拟 0.6 秒后真的去开
    assert opened and opened[0].startswith("http://127.0.0.1:")

    # 关掉的方式：环境变量（打包态唯一能塞的地方）
    opened.clear()
    timers.clear()
    monkeypatch.setenv("POJIA_GUI_NO_OPEN", "1")
    assert gui.main() == 0
    assert timers == [] and opened == []


class _FakeServer:
    """替掉真的 ThreadingHTTPServer：不绑端口、不进事件循环。"""

    def __init__(self, addr, handler):
        self.server_address = ("127.0.0.1", 12345)

    def serve_forever(self):
        raise KeyboardInterrupt          # 立刻退出，别把测试挂住

    def server_close(self):
        pass

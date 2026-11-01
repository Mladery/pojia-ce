# -*- coding: utf-8 -*-
"""macOS 那一段：.app 是被整体签名的，改里面的文件就得重签。

这些断言钉的是**真实会咬人的那条线**，不是代码覆盖率：

  · 破甲往 .app 里写了东西（asar 解包目录 / managed-prompts / .bak），签名 seal
    就不匹配了。带 quarantine 的包（刚下载、没启动过）再启动，Gatekeeper 直接报
    「已损坏，无法打开」—— 上游 macOS 版 v1.0.9 专门为此加了 ad-hoc 重签。
  · 重签必须**只在本轮真动过包内文件时**发生。守护任务每 5 分钟写一次
    ~/.workbuddy，那在包外面；要是每次都签，就是每 5 分钟扫几百 MB，纯属自残。
  · 非 macOS 上一个字节都不许动，更不许凭空报「签名坏了」。
"""
import os
import sys
import types

import pytest


# --------------------------------------------------------------- 包路径识别

def test_app_bundle_of_finds_enclosing_bundle(core, tmp_path):
    """路径落在 .app 里就返回那个 .app —— 深层嵌套也要认出来。"""
    app = tmp_path / "DSH Desktop.app"
    inside = app / "Contents" / "Resources" / "app" / "dsh" / "x.js"
    assert core.app_bundle_of(str(inside)) == str(app)
    assert core.app_bundle_of(str(app)) == str(app)
    assert core.app_bundle_of(str(app / "Contents" / "MacOS" / "DSH")) == str(app)


def test_app_bundle_of_returns_empty_outside_bundle(core, tmp_path):
    """包外的路径一律空 —— 守护任务写的 ~/.workbuddy 就在这里，绝不能被记成要重签。"""
    assert core.app_bundle_of(str(tmp_path / ".workbuddy" / "plugins" / "x.js")) == ""
    assert core.app_bundle_of("") == ""
    assert core.app_bundle_of(None) == ""


def test_app_bundle_of_ignores_names_that_only_contain_dot_app(core, tmp_path):
    """`.app` 必须是一个完整路径段，不能被 `my.appdata` 这种名字骗到。"""
    assert core.app_bundle_of(str(tmp_path / "my.appdata" / "x.js")) == ""
    assert core.app_bundle_of(str(tmp_path / "notes.app.txt")) == ""


# --------------------------------------------------------------- 只读体检

def test_codesign_verify_is_a_noop_off_macos(core, monkeypatch):
    """非 macOS 上不许跑 codesign，也不许报「签名坏了」。"""
    monkeypatch.setattr(core, "IS_MAC", False)
    called = []
    monkeypatch.setattr(core, "_run_quiet", lambda *a, **k: called.append(a) or (1, "boom"))
    ok, note = core.codesign_verify("/Applications/X.app")
    assert ok is True
    assert "非 macOS" in note
    assert called == [], "非 macOS 上居然真的去跑 codesign 了"


def test_codesign_verify_reports_failure(core, monkeypatch):
    monkeypatch.setattr(core, "IS_MAC", True)
    seen = {}

    def fake(cmd, timeout):
        seen["cmd"] = cmd
        return 1, "code object is not signed at all\nIn subcomponent: /X.app/Contents/MacOS/X"

    monkeypatch.setattr(core, "_run_quiet", fake)
    ok, note = core.codesign_verify("/Applications/X.app")
    assert ok is False
    assert "not signed" in note
    assert seen["cmd"][:3] == ["codesign", "--verify", "--strict"]


def test_codesign_verify_missing_tool_is_not_a_failure(core, monkeypatch):
    """机器上没有 codesign（精简系统）时按 ok 处理 —— 宁可漏报，不要瞎报警。"""
    monkeypatch.setattr(core, "IS_MAC", True)
    monkeypatch.setattr(core, "_run_quiet", lambda *a, **k: (None, "no such file"))
    ok, note = core.codesign_verify("/Applications/X.app")
    assert ok is True
    assert "不可用" in note


def test_codesign_adhoc_uses_dash_identity(core, monkeypatch):
    """ad-hoc 的身份就是一个 `-`：不依赖任何证书，本机自签。"""
    monkeypatch.setattr(core, "IS_MAC", True)
    seen = {}

    def fake(cmd, timeout):
        seen["cmd"] = cmd
        return 0, ""

    monkeypatch.setattr(core, "_run_quiet", fake)
    ok, _ = core.codesign_adhoc("/Applications/X.app")
    assert ok is True
    assert seen["cmd"] == ["codesign", "--force", "--deep", "--sign", "-", "/Applications/X.app"]


# --------------------------------------------------------------- 何时才重签

def test_touch_records_bundle_only_on_macos(core, monkeypatch, tmp_path):
    app = tmp_path / "X.app"
    inside = str(app / "Contents" / "Resources" / "app" / "a.js")

    monkeypatch.setattr(core, "_MAC_TOUCHED", set())
    monkeypatch.setattr(core, "IS_MAC", True)
    core._mac_touch(inside)
    assert core._MAC_TOUCHED == {str(app)}

    monkeypatch.setattr(core, "_MAC_TOUCHED", set())
    monkeypatch.setattr(core, "IS_MAC", False)
    core._mac_touch(inside)
    assert core._MAC_TOUCHED == set(), "非 macOS 上不该记任何东西"


def test_write_text_touches_bundle(core, monkeypatch, tmp_path):
    """写入是唯一的收口：往 .app 里写一个字，就得记下这个包。"""
    monkeypatch.setattr(core, "_MAC_TOUCHED", set())
    monkeypatch.setattr(core, "IS_MAC", True)
    monkeypatch.setattr(core, "DRY_RUN", False)
    app = tmp_path / "X.app"
    (app / "Contents").mkdir(parents=True)
    target = app / "Contents" / "a.txt"
    assert core.write_text(str(target), "hi") is True
    assert core._MAC_TOUCHED == {str(app)}


def test_dry_run_never_touches_bundle(core, monkeypatch, tmp_path):
    """预演一个字节都不写，也就绝不该在收尾时去签一遍包。"""
    monkeypatch.setattr(core, "_MAC_TOUCHED", set())
    monkeypatch.setattr(core, "IS_MAC", True)
    monkeypatch.setattr(core, "DRY_RUN", True)
    core.write_text(str(tmp_path / "X.app" / "a.txt"), "hi")
    assert core._MAC_TOUCHED == set()


def test_resign_only_when_something_was_touched(core, monkeypatch):
    """守护任务每 5 分钟写一次包外的文件 —— 那种情况下一次 codesign 都不该跑。"""
    monkeypatch.setattr(core, "IS_MAC", True)
    monkeypatch.setattr(core, "_MAC_TOUCHED", set())
    calls = []
    monkeypatch.setattr(core, "codesign_adhoc", lambda p: calls.append(p) or (True, ""))
    core.mac_resign_touched()
    assert calls == [], "什么都没动却去重签了"

    monkeypatch.setattr(core, "_MAC_TOUCHED", {"/Applications/X.app", "/Applications/Y.app"})
    core.mac_resign_touched()
    assert calls == ["/Applications/X.app", "/Applications/Y.app"]
    assert core._MAC_TOUCHED == set(), "签完要清空，否则同一进程里跑第二次会重复签"


def test_resign_failure_prints_manual_command(core, monkeypatch, capsys):
    """签失败不能只吞掉 —— 得把能救回来的命令原样给出来。"""
    monkeypatch.setattr(core, "IS_MAC", True)
    monkeypatch.setattr(core, "_MAC_TOUCHED", {"/Applications/X.app"})
    monkeypatch.setattr(core, "codesign_adhoc", lambda p: (False, "resource fork busy"))
    core.mac_resign_touched()
    out = capsys.readouterr().out
    assert "resource fork busy" in out
    assert "codesign --force --deep --sign -" in out
    assert "xattr -cr" in out


def test_resign_is_a_noop_off_macos(core, monkeypatch):
    monkeypatch.setattr(core, "IS_MAC", False)
    monkeypatch.setattr(core, "_MAC_TOUCHED", {"/Applications/X.app"})
    calls = []
    monkeypatch.setattr(core, "codesign_adhoc", lambda p: calls.append(p) or (True, ""))
    core.mac_resign_touched()
    assert calls == []


# --------------------------------------------------------------- 候选扫描

def test_mac_app_candidates_filters_by_hint(core, tmp_path):
    apps = tmp_path / "Applications"
    apps.mkdir()
    for name in ("DSH Desktop.app", "WorkBuddy.app", "Safari.app", "Notes.txt"):
        p = apps / name
        if name.endswith(".app"):
            p.mkdir()
        else:
            p.write_text("x", encoding="utf-8")
    got = core.mac_app_candidates(dirs=[str(apps)])
    names = [os.path.basename(p) for p in got]
    assert "DSH Desktop.app" in names
    assert "WorkBuddy.app" in names
    assert "Safari.app" not in names, "不认得的包不该进候选，更不该被重签"
    assert "Notes.txt" not in names


def test_mac_check_off_macos_says_so(core, monkeypatch, capsys):
    monkeypatch.setattr(core, "IS_MAC", False)
    assert core.run_mac_check(types.SimpleNamespace(resign=False)) == 0
    assert "只在 macOS 上有意义" in capsys.readouterr().out

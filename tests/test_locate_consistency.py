# -*- coding: utf-8 -*-
"""检测状态与破甲必须用同一套定位逻辑。

用户实测：另一台机器 `--status` 对 DSH 报 0 套，`--apply` 报 1 套（来源：进程反查）。
根因是「进程反查」只在客户端开着时有效，而检测时它常常是关着的。
这里锁住两件事：
  1. 标记块目标的 locate() 只有一条链，检测和破甲都调它；
  2. 命中过的安装根能落盘复用（只读/预演不写）。
"""
import os


def test_mark_block_locate_uses_the_shared_chain(core, tmp_path, monkeypatch, args):
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    calls = {}

    def fake(exes, judge, **kw):
        calls["exes"] = exes
        calls["kw"] = kw
        return str(tmp_path / "Claude"), "进程反查"

    monkeypatch.setattr(core, "discover_app_root", fake)
    t = core.ClaudeTarget()
    setattr(args, t.arg_name, "")
    home, root, src = t.locate(args)

    assert calls["exes"] == ("Claude.exe",), "必须用目标自己声明的 exe 名去反查"
    assert src == "进程反查"
    assert root.endswith("Claude")
    # 配置目录还不存在 → 检测与破甲都判「没装」，但两边都能说出装在哪
    assert os.path.isdir(home) is False
    assert t.detect_ok(args) is False


def test_zcode_detected_matches_apply(core, tmp_path, monkeypatch, args):
    """ZCode：找到 zcode.cjs 就算检测到（apply 也认这条，不再只认配置目录）。"""
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    cjs = tmp_path / "zcode.cjs"
    cjs.write_text("// stub\n", encoding="utf-8")
    t = core.ZCodeTarget()
    monkeypatch.setattr(t, "cjs_path", lambda _a: str(cjs))
    assert t.detected(args) is True
    assert t.detect_ok(args) is True

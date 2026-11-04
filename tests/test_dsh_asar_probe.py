# -*- coding: utf-8 -*-
"""DSH 只读探测：插件只存在于 app.asar 里时，检测状态不能报 0。

用户实测踩到：另一台机器 `--status` 报 0 个安装，`--apply` 解包后报 1 个。
根因是发现阶段只有真解包才看得见插件，而只读路径不解包 —— 于是同一台机器
两种说法。修法：只读时读 asar 头（便宜、不写盘），把这种安装记进 asar_only。
"""
import json
import os
import struct


def _fake_asar(path, with_agent=True):
    """写一个只有头、没有数据区的 asar。返回的树决定「里面有没有插件」。"""
    empty = {"files": {}}
    if with_agent:
        tree = {"files": {"dsh": {"files": {"node_modules": {"files": {
            "@deepseek-ai": {"files": {"dsh-agent-instructions": empty}}}}}}}}
    else:
        tree = {"files": {"main.js": {"size": 0, "offset": "0"}}}
    payload = json.dumps(tree).encode("utf-8")
    # 头 16 字节：前 12 字节是 Chromium pickle 头，本工具只读偏移 12 的 json 长度。
    with open(path, "wb") as f:
        f.write(b"\x00" * 12 + struct.pack("<I", len(payload)) + payload)


def _install(tmp_path, with_agent=True):
    root = tmp_path / "DSH Desktop"
    res = root / "resources"
    res.mkdir(parents=True)
    (root / "DSH Desktop.exe").write_bytes(b"")
    _fake_asar(str(res / "app.asar"), with_agent)
    return str(root), str(res)


def test_asar_only_counts_as_install(core, tmp_path, monkeypatch, args):
    root, res = _install(tmp_path)
    t = core.DshTarget()
    t.asar_only = []
    t._note_asar_only(res)
    assert t.asar_only == [root], "插件在 asar 里，必须记成一套安装"

    # 只读路径拿不到可改目录，但「检测到没有」必须为真 —— 否则 --status 报 0
    monkeypatch.setattr(t, "find_bases", lambda *_a, **_k: [])
    assert t.detect_ok(args) is True


def test_asar_without_agent_is_ignored(core, tmp_path):
    _root, res = _install(tmp_path, with_agent=False)
    t = core.DshTarget()
    t.asar_only = []
    t._note_asar_only(res)
    assert t.asar_only == [], "asar 里没有桌面端插件就不该算"


def test_already_unpacked_is_not_double_counted(core, tmp_path):
    """resources/app 已经解出来了（find_bases 收得到靶点），就不能再记一次。"""
    _root, res = _install(tmp_path)
    mark = os.path.join(res, "app", "dsh", "node_modules", "@deepseek-ai")
    os.makedirs(os.path.join(mark, "dsh-agent-instructions"))
    t = core.DshTarget()
    t.asar_only = []
    t._note_asar_only(res)
    assert t.asar_only == [], "已解包的不能再算一套，否则 status 比 apply 多"


def test_check_says_how_many_installs(core, tmp_path, monkeypatch, args):
    """check() 在只有 asar 的情况下要报数量，不能只说「没探测到」。"""
    root, _res = _install(tmp_path)
    t = core.DshTarget()
    t.asar_only = [root]
    monkeypatch.setattr(t, "find_bases", lambda *_a, **_k: [])
    rows = t.check(args)
    notes = " ".join(n for _st, n, _d in rows)
    assert "1 套" in notes and "app.asar" in notes, notes
    assert "没探测到" not in notes


def test_found_path_cache_only_written_by_write_paths(core, tmp_path, monkeypatch):
    """`--status` 承诺不改盘：命中缓存只能由写盘路径落，只读/预演一律不写。"""
    root, _res = _install(tmp_path)
    state = tmp_path / "state"
    monkeypatch.setattr(core, "STATE_DIR", str(state))
    monkeypatch.setattr(core, "FOUND_PATH_FILE", str(state / "发现目录.json"))

    monkeypatch.setattr(core, "READONLY", True)
    core.remember_found("dsh", root, "进程反查")
    assert core.get_found_path("dsh") == "", "只读路径不许写缓存"

    monkeypatch.setattr(core, "READONLY", False)
    monkeypatch.setattr(core, "DRY_RUN", True)
    core.remember_found("dsh", root, "进程反查")
    assert core.get_found_path("dsh") == "", "预演也不许写缓存"

    monkeypatch.setattr(core, "DRY_RUN", False)
    core.remember_found("dsh", root, "进程反查")
    assert core.get_found_path("dsh") == root, "真破甲命中后要留下来给下次检测用"

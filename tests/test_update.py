"""自动更新的只读面：版本比较、资产选择、校验、缓存。"""
import hashlib
import json
import os
import sys
import types

import pytest


def test_ver2_parses_release_tag(core):
    assert core._ver2("v8.63-CE") == (8, 63)
    assert core._ver2("8.9") == (8, 9)
    assert core._ver2("") == (0, 0)
    # 8.9 要大于 8.10 之外的判断交给元组本身：9 > 10 不成立，这里钉住的是
    # 「按数字段比而不是按字符串比」。
    assert core._ver2("8.10") > core._ver2("8.9")


def test_asset_name_follows_platform(core, monkeypatch):
    monkeypatch.setattr(core.os, "name", "nt")
    assert core.update_asset() == "pojia-ce-windows-x64.exe"
    monkeypatch.setattr(core.os, "name", "posix")
    monkeypatch.setattr(core, "IS_MAC", False)
    assert core.update_asset() == "pojia-ce-linux-x64"
    monkeypatch.setattr(core, "IS_MAC", True)
    monkeypatch.setattr(core.platform, "machine", lambda: "x86_64")
    assert core.update_asset() == "pojia-ce-macos-x64"
    monkeypatch.setattr(core.platform, "machine", lambda: "arm64")
    assert core.update_asset() == "pojia-ce-macos-arm64"


def test_update_check_reads_tag_and_assets(core, monkeypatch):
    payload = {
        "tag_name": "v8.70-CE",
        "assets": [{"name": "pojia-ce-linux-x64", "browser_download_url": "https://x/y"}],
    }
    monkeypatch.setattr(core, "_http_get", lambda url, timeout=8: json.dumps(payload).encode())
    ver, assets, err = core.update_check()
    assert (ver, err) == ("8.70", "")
    assert assets["pojia-ce-linux-x64"] == "https://x/y"


def test_update_check_reports_network_error(core, monkeypatch):
    def boom(url, timeout=8):
        raise OSError("no route")

    monkeypatch.setattr(core, "_http_get", boom)
    ver, assets, err = core.update_check()
    assert ver == "" and assets == {} and "no route" in err


def test_download_verifies_sha256(core, monkeypatch, tmp_path):
    blob = b"fake-binary"
    good = hashlib.sha256(blob).hexdigest()
    table = "%s  pojia-ce-linux-x64\n" % good

    def fake(url, timeout=8):
        return table.encode() if url.endswith("SHA256SUMS.txt") else blob

    monkeypatch.setattr(core, "_http_get", fake)
    monkeypatch.setattr(core, "update_asset", lambda: "pojia-ce-linux-x64")
    dst = str(tmp_path / "new.bin")
    ok, msg = core.update_download({"pojia-ce-linux-x64": "u", "SHA256SUMS.txt": "s"}, dst)
    assert ok, msg
    assert open(dst, "rb").read() == blob


def test_download_refuses_on_mismatch(core, monkeypatch, tmp_path):
    monkeypatch.setattr(core, "_http_get", lambda url, timeout=8:
                        b"deadbeef  pojia-ce-linux-x64\n" if url == "s" else b"payload")
    monkeypatch.setattr(core, "update_asset", lambda: "pojia-ce-linux-x64")
    dst = str(tmp_path / "new.bin")
    ok, msg = core.update_download({"pojia-ce-linux-x64": "u", "SHA256MB": "s", "SHA256SUMS.txt": "s"}, dst)
    assert not ok and "校验不符" in msg
    assert not os.path.exists(dst)


def test_download_without_checksum_still_installs(core, monkeypatch, tmp_path):
    monkeypatch.setattr(core, "_http_get", lambda url, timeout=8: b"blob")
    monkeypatch.setattr(core, "update_asset", lambda: "pojia-ce-linux-x64")
    dst = str(tmp_path / "new.bin")
    ok, msg = core.update_download({"pojia-ce-linux-x64": "u"}, dst)
    assert ok and "无校验和" in msg


def test_run_update_says_uptodate(core, monkeypatch, capsys):
    monkeypatch.setattr(core, "update_check", lambda timeout=8: (core.VERSION, {}, ""))
    monkeypatch.setattr(core, "QUIET", False)
    monkeypatch.setattr(core, "_C", {})
    assert core.run_update() == 0


def test_run_update_check_only_does_not_download(core, monkeypatch):
    called = []
    monkeypatch.setattr(core, "update_check", lambda timeout=8: ("99.99", {"a": "b"}, ""))
    monkeypatch.setattr(core, "update_download", lambda *a, **k: called.append(1) or (True, "x"))
    monkeypatch.setattr(core, "QUIET", True)
    assert core.run_update(check_only=True) == 0
    assert called == []


def test_install_refuses_outside_frozen(core, monkeypatch, tmp_path):
    monkeypatch.setattr(core.sys, "frozen", False, raising=False)
    ok, msg = core.update_install(str(tmp_path / "x"))
    assert not ok and "源码运行" in msg


def test_install_windows_bat_waits_and_takes_over(core, monkeypatch, tmp_path):
    """Windows 上不能自己覆盖自己，得留一个等进程退出的批处理。

    两个钉点：行尾只能是 CRLF（`\\r\\r\\n` 会让 cmd 读歪），并且必须先等
    `move` 成功才换文件 —— 早一步就是「文件正被另一个程序使用」。
    """
    spawned = []
    monkeypatch.setattr(core.sys, "frozen", True, raising=False)
    monkeypatch.setattr(core, "SELF", str(tmp_path / "pojia-ce.exe"))
    monkeypatch.setattr(core, "HERE", str(tmp_path))
    monkeypatch.setattr(core.os, "name", "nt")
    monkeypatch.setattr(core.subprocess, "Popen", lambda *a, **k: spawned.append(a))
    ok, msg = core.update_install(str(tmp_path / "new.exe"))
    assert ok, msg
    raw = open(str(tmp_path / "_update.bat"), "rb").read()
    assert b"\r\r\n" not in raw
    txt = raw.decode("utf-8")
    assert ":wait" in txt and "goto wait" in txt
    assert txt.index(":wait") < txt.index('move /y "%s"' % (tmp_path / "new.exe"))
    assert spawned, "没起批处理，替换永远不会发生"

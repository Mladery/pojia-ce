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
        return table.encode() if url == "s" else blob

    monkeypatch.setattr(core, "_http_get", fake)
    monkeypatch.setattr(core, "update_asset", lambda: "pojia-ce-linux-x64")
    dst = str(tmp_path / "new.bin")
    ok, msg = core.update_download({"pojia-ce-linux-x64": "u", "SHA256SUMS.txt": "s"}, dst)
    assert ok, msg
    assert "无校验和" not in msg            # 真比过了，不是「没表可依」蒙过去的
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


def test_download_matches_sha256sum_dot_slash_form(core, monkeypatch, tmp_path):
    """构建脚本写的是 `sha256sum ./*`，条目形如 `hash  ./文件名`。"""
    blob = b"real-binary"
    table = ("%s  ./pojia-ce-linux-x64\n"
             "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  ./SHA256SUMS.txt\n"
             % hashlib.sha256(blob).hexdigest())
    monkeypatch.setattr(core, "_http_get", lambda url, timeout=8: table.encode() if url == "s" else blob)
    monkeypatch.setattr(core, "update_asset", lambda: "pojia-ce-linux-x64")
    dst = str(tmp_path / "new.bin")
    ok, msg = core.update_download({"pojia-ce-linux-x64": "u", "SHA256SUMS.txt": "s"}, dst)
    assert ok, msg
    assert "无校验和" not in msg          # 命中就是命中，不能悄悄退化成不校验


def test_download_refuses_when_table_lacks_entry(core, monkeypatch, tmp_path):
    """表能读到但没有这一行 —— 发布不全，不装。"""
    monkeypatch.setattr(core, "_http_get", lambda url, timeout=8:
                        b"deadbeef  ./other-file\n" if url == "s" else b"blob")
    monkeypatch.setattr(core, "update_asset", lambda: "pojia-ce-linux-x64")
    dst = str(tmp_path / "new.bin")
    ok, msg = core.update_download({"pojia-ce-linux-x64": "u", "SHA256SUMS.txt": "s"}, dst)
    assert not ok and "没有" in msg and not os.path.exists(dst)


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


def test_hint_off_with_flag(core, monkeypatch):
    """--no-update-check：一个请求都不该发出去。"""
    def boom(timeout=8):
        raise AssertionError("关了还联网")

    monkeypatch.setattr(core, "update_check", boom)
    core.update_hint(type("A", (), {"no_update_check": True})())


def test_hint_off_with_env(core, monkeypatch):
    monkeypatch.setenv("POJIA_NO_UPDATE_CHECK", "1")

    def boom(timeout=8):
        raise AssertionError("关了还联网")

    monkeypatch.setattr(core, "update_check", boom)
    core.update_hint(None)


def test_hint_prints_once_then_caches(core, monkeypatch, tmp_path, capsys):
    """查到新版只打印一行提示，并把结果缓存一天 —— 第二次不再发请求。"""
    monkeypatch.delenv("POJIA_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(core, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(core, "QUIET", False)
    monkeypatch.setattr(core, "_C", {})
    calls = []

    def fake(timeout=8):
        calls.append(1)
        return "9.99", {}, ""

    monkeypatch.setattr(core, "update_check", fake)
    core.update_hint(None)
    out = capsys.readouterr().out
    assert "9.99" in out and "--update" in out
    assert os.path.isfile(str(tmp_path / "_update.json"))
    assert calls == [1]

    core.update_hint(None)                    # 缓存命中，不再请求
    assert calls == [1]


def test_hint_quiet_when_up_to_date(core, monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("POJIA_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(core, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(core, "QUIET", False)
    monkeypatch.setattr(core, "_C", {})
    monkeypatch.setattr(core, "update_check", lambda timeout=8: (core.VERSION, {}, ""))
    core.update_hint(None)
    assert "有新版本" not in capsys.readouterr().out


def test_hint_survives_network_error(core, monkeypatch, tmp_path, capsys):
    """没网 / 限流时安静跳过，不能把启动流程带崩。"""
    monkeypatch.delenv("POJIA_NO_UPDATE_CHECK", raising=False)
    monkeypatch.setattr(core, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(core, "QUIET", False)
    monkeypatch.setattr(core, "_C", {})

    def boom(url, timeout=8):
        raise OSError("no route")

    monkeypatch.setattr(core, "_http_get", boom)
    core.update_hint(None)
    assert "错误" not in capsys.readouterr().out


# ---- POSIX 安装态：install.json 是唯一的判据 -------------------------------

def _fake_install(core, monkeypatch, tmp_path, prefix=""):
    """把 HERE 指到临时目录，并按需写一份 install.json。"""
    monkeypatch.setattr(core, "HERE", str(tmp_path))
    if prefix is not None:
        (tmp_path / "install.json").write_text(
            json.dumps({"prefix": prefix or str(tmp_path), "version": "8.65"},
                       ensure_ascii=False), encoding="utf-8")


def test_install_meta_reads_own_prefix(core, monkeypatch, tmp_path):
    _fake_install(core, monkeypatch, tmp_path)
    assert core.install_meta().get("version") == "8.65"


def test_install_meta_ignores_copied_dir(core, monkeypatch, tmp_path):
    """装好的目录被整个复制走，副本里 prefix 对不上 —— 那份按绿色版处理。

    不然升级会往副本目录里铺一整套，用户以为在升原件。
    """
    _fake_install(core, monkeypatch, tmp_path, prefix="/somewhere/else/pojia-ce")
    assert core.install_meta() == {}


def test_installed_mode_posix_uses_meta(core, monkeypatch, tmp_path):
    monkeypatch.setattr(core.os, "name", "posix")
    _fake_install(core, monkeypatch, tmp_path)
    assert core.installed_mode() is True
    (tmp_path / "install.json").unlink()
    assert core.installed_mode() is False


def test_asset_prefers_installer_when_installed(core, monkeypatch, tmp_path):
    """装出来的下安装包，绿色版下裸二进制 —— 拿错的会丢 _internal。"""
    monkeypatch.setattr(core.os, "name", "posix")
    monkeypatch.setattr(core, "IS_MAC", False)
    _fake_install(core, monkeypatch, tmp_path)
    assert core.update_asset() == "pojia-ce-linux-x64-installer.run"
    monkeypatch.setattr(core, "IS_MAC", True)
    monkeypatch.setattr(core.platform, "machine", lambda: "arm64")
    assert core.update_asset() == "pojia-ce-macos-arm64-installer.command"
    monkeypatch.setattr(core.platform, "machine", lambda: "x86_64")
    assert core.update_asset() == "pojia-ce-macos-x64-installer.command"


def test_unix_install_schedules_installer(core, monkeypatch, tmp_path):
    """安装版自更新不能直接 os.replace：新版的 _internal 会有多余的库。"""
    monkeypatch.setattr(core.os, "name", "posix")
    monkeypatch.setattr(core.sys, "frozen", True, raising=False)
    monkeypatch.setattr(core, "SELF", str(tmp_path / "pojia-ce"))
    _fake_install(core, monkeypatch, tmp_path)
    calls = []
    monkeypatch.setattr(core.subprocess, "Popen", lambda *a, **k: calls.append(a))

    ok, msg = core.update_install("/tmp/new-installer.run")
    assert ok and "静默安装" in msg
    sh = (tmp_path / "_update.sh").read_text(encoding="utf-8")
    assert "/tmp/new-installer.run" in sh and "--yes" in sh
    assert "pojia-ce" in sh
    assert calls, "没把更新脚本拉起来"

"""Windows bash 接管：内嵌 busybox、插件生成、配置字段。"""
import hashlib
import os
import re
import shutil
import subprocess

import pytest


def test_busybox_is_embedded_and_intact(core):
    """内嵌的二进制要能解压出来，且和记录的指纹一致。"""
    data = core.busybox_bytes()
    assert len(data) > 500_000
    assert hashlib.sha256(data).hexdigest() == core.BUSYBOX_SHA256
    assert data[:2] == b"MZ"          # 是 PE，不是文本


def test_write_busybox_is_idempotent(core, tmp_path):
    p = str(tmp_path / "sub" / "busybox64.exe")
    assert core._write_busybox(p) == p
    first = os.stat(p).st_mtime_ns
    size = os.path.getsize(p)
    # 再次调用不重写：大小已经对得上就直接返回
    assert core._write_busybox(p) == p
    assert os.stat(p).st_mtime_ns == first
    assert os.path.getsize(p) == size


def test_patch_text_carries_busybox(core, tmp_path):
    txt = core.gitbash_patch_text(r"C:\Program Files\Git\bin\bash.exe",
                                  str(tmp_path / "busybox64.exe"))
    assert "busybox:" in txt
    assert "disabled: false" in txt and "tool-pwsh" in txt
    # 不带 busybox 时不该凭空造字段
    assert "busybox:" not in core.gitbash_patch_text("x")


def test_plugin_declares_ash_and_system_prompt(core):
    js = core.GITBASH_JS
    assert "executeArgv" in js                   # 换 shell 的挂点
    assert "busybox ash" in js                   # 系统提示里讲清楚是 ash
    assert '"systemPrompt"' in js
    assert '"shell"' in js
    # 只换 bash，别的命令原样透传
    assert '"bash"' in js


def test_plugin_is_valid_esm(core, tmp_path):
    """用 node --check 过一遍语法。没装 node 就跳过。"""
    node = shutil.which("node")
    if not node:
        pytest.skip("没有 node，跳过语法检查")
    p = tmp_path / "gitbash.mjs"
    p.write_text(core.GITBASH_JS, encoding="utf-8")
    r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_install_writes_plugin_and_records_busybox(core, tmp_path, monkeypatch):
    home = str(tmp_path / "dsh")
    prof = os.path.join(home, "profiles", "desktop")
    os.makedirs(prof)
    yml = os.path.join(prof, "cordis.patch.yml")
    open(yml, "w", encoding="utf-8").write("# base\n")
    monkeypatch.setattr(core, "preset_std_text", lambda *a, **k: ("", ""))

    ok, msg = core.gitbash_install(home, r"C:\Program Files\Git\bin\bash.exe")
    assert ok, msg

    txt = open(yml, encoding="utf-8").read()
    m = re.search(r'busybox:\s*"(.+?)"', txt)
    assert m, txt
    bb = m.group(1).replace("\\\\", "\\")
    assert os.path.isfile(bb) and os.path.getsize(bb) == len(core.busybox_bytes())

    pkg = os.path.join(prof, "node_modules", core.GITBASH_ID)
    for f in ("package.json", "index.js", "busybox64.exe"):
        assert os.path.isfile(os.path.join(pkg, f)), f


def test_install_is_repeatable(core, tmp_path, monkeypatch):
    home = str(tmp_path / "dsh")
    prof = os.path.join(home, "profiles", "desktop")
    os.makedirs(prof)
    yml = os.path.join(prof, "cordis.patch.yml")
    open(yml, "w", encoding="utf-8").write("# base\n")
    monkeypatch.setattr(core, "preset_std_text", lambda *a, **k: ("", ""))
    for _ in range(3):
        ok, msg = core.gitbash_install(home, r"C:\Program Files\Git\bin\bash.exe")
        assert ok, msg
    txt = open(yml, encoding="utf-8").read()
    assert txt.count("# >>> " + core.GITBASH_MARK) == 1     # 反复装只有一段，不堆叠
    assert txt.count("# <<< " + core.GITBASH_MARK) == 1


def test_state_mentions_busybox(core, tmp_path, monkeypatch):
    home = str(tmp_path / "dsh")
    prof = os.path.join(home, "profiles", "desktop")
    os.makedirs(prof)
    yml = os.path.join(prof, "cordis.patch.yml")
    open(yml, "w", encoding="utf-8").write("# base\n")
    monkeypatch.setattr(core, "preset_std_text", lambda *a, **k: ("", ""))
    monkeypatch.setattr(core, "git_bash_probe", lambda exe: ("5.2.0", "MINGW64"))
    core.gitbash_install(home, r"C:\Program Files\Git\bin\bash.exe")
    st, note, _exe = core.gitbash_state(home)
    assert st == "ok" and "ash" in note

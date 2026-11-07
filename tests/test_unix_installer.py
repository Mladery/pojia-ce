"""Linux / macOS 自解压安装包：载荷拼接、权限、脚本语法、装/升流程。"""
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "build_unix_installer.py")
MARK = b"__POJIA_PAYLOAD_BELOW__\n"


@pytest.fixture(scope="module")
def tool():
    spec = importlib.util.spec_from_file_location("pojia_buix", TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture
def src(tmp_path):
    """伪造一个 onedir 产物：可执行主程序 + _internal/ 里的一个库。"""
    d = tmp_path / "pojia-ce"
    (d / "_internal").mkdir(parents=True)
    exe = d / "pojia-ce"
    exe.write_text('#!/bin/sh\n[ "$1" = "--version" ] && echo 破甲一键通 8.65-CE\n')
    exe.chmod(0o755)
    (d / "_internal" / "libpython3.11.so").write_bytes(b"\x7fELF fake")
    return str(d)


def test_build_writes_executable_with_version(tool, src, tmp_path):
    out = str(tmp_path / "x.run")
    assert tool.build(src, "linux-x64", out) == 0
    assert os.access(out, os.X_OK)
    head = open(out, "rb").read(4096).decode("utf-8", "replace")
    assert 'VERSION="8.65-CE"' in head
    assert 'ASSET="linux-x64"' in head
    assert "__VERSION__" not in head


def test_payload_starts_right_after_marker(tool, src, tmp_path):
    """偏移算错一位，装的时候就解不出包。这里钉住「标记下一行就是 gzip」。"""
    out = str(tmp_path / "x.run")
    tool.build(src, "linux-x64", out)
    blob = open(out, "rb").read()
    # 头部 awk 那行写的是 /^__...__$/，后面紧跟 $/'，不匹配带换行的这个常量。
    assert blob.count(MARK) == 1
    i = blob.rindex(MARK) + len(MARK)
    assert blob[i:i + 2] == b"\x1f\x8b"


def test_payload_keeps_exec_bit_and_ownership(tool, src, tmp_path):
    out = str(tmp_path / "x.run")
    tool.build(src, "linux-x64", out)
    blob = open(out, "rb").read()
    i = blob.rindex(MARK) + len(MARK)
    with tarfile.open(fileobj=io.BytesIO(blob[i:]), mode="r:gz") as tar:
        assert "pojia-ce/pojia-ce" in tar.getnames()
        ti = tar.getmember("pojia-ce/pojia-ce")
        assert ti.mode & 0o111, "可执行位丢了，装上也跑不起来"
        # 构建机的用户名不该跟着产物走
        assert (ti.uid, ti.uname) == (0, "root")


def test_default_name_follows_platform(tool):
    assert tool.default_out("linux-x64").endswith("-installer.run")
    assert tool.default_out("macos-arm64").endswith("-installer.command")


def test_refuses_dir_without_internal(tool, tmp_path):
    """单文件产物没有 _internal/，装出来缺依赖 —— 构建时就拒绝。"""
    d = tmp_path / "pojia-ce"
    d.mkdir()
    (d / "pojia-ce").write_bytes(b"x")
    assert tool.build(str(d), "linux-x64", str(tmp_path / "x.run")) == 1


@pytest.mark.skipif(not shutil.which("sh"), reason="没有 sh")
def test_head_is_valid_sh(tool, src, tmp_path):
    """只解析头部 —— 载荷是二进制，整文件喂给 sh -n 必然报错。"""
    out = str(tmp_path / "x.run")
    tool.build(src, "linux-x64", out)
    head = open(out, "rb").read().split(MARK)[0]
    p = tmp_path / "head.sh"
    p.write_bytes(head)
    r = subprocess.run(["sh", "-n", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX 安装器，只在 Linux/macOS 上跑")
def test_install_then_upgrade_keeps_data(tool, src, tmp_path):
    out = str(tmp_path / "x.run")
    tool.build(src, "linux-x64", out)
    home = tmp_path / "home"
    home.mkdir()
    app = home / "app"
    env = dict(os.environ, HOME=str(home))

    r = subprocess.run(["sh", out, "--yes", "--quiet", "--prefix", str(app)],
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert os.access(str(app / "pojia-ce"), os.X_OK)
    assert (app / "_internal" / "libpython3.11.so").is_file()
    meta = json.load(open(app / "install.json", encoding="utf-8"))
    assert meta["version"] == "8.65-CE" and meta["prefix"] == str(app)
    assert os.path.islink(str(home / ".local" / "bin" / "pojia-ce"))

    # 再跑一遍 = 升级。用户数据必须跟着走，不能被新目录顶掉。
    (app / "状态").mkdir()
    (app / "状态" / "探针.txt").write_text("keep", encoding="utf-8")
    (app / "persona.md").write_text("自定义人格", encoding="utf-8")
    r2 = subprocess.run(["sh", out, "--yes", "--quiet", "--prefix", str(app)],
                        capture_output=True, text=True, env=env)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert (app / "状态" / "探针.txt").read_text(encoding="utf-8") == "keep"
    assert (app / "persona.md").read_text(encoding="utf-8") == "自定义人格"


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX 安装器")
def test_refuses_foreign_dir(tool, src, tmp_path):
    """目标目录里已经有别人的东西时拒绝写入 —— 下面可是 rm -rf。"""
    out = str(tmp_path / "x.run")
    tool.build(src, "linux-x64", out)
    home = tmp_path / "home"
    home.mkdir()
    app = home / "app"
    app.mkdir()
    (app / "别人的东西.txt").write_text("x", encoding="utf-8")
    r = subprocess.run(["sh", out, "--yes", "--quiet", "--prefix", str(app)],
                       capture_output=True, text=True,
                       env=dict(os.environ, HOME=str(home)))
    assert r.returncode != 0
    assert (app / "别人的东西.txt").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX 安装器")
def test_braced_var_before_cjk_is_intact():
    """macOS 的 /bin/sh 是 bash 3.2：`$VAR` 后面紧贴中文时，它会把那个字的
    首字节吃进变量名（变量变成 VAR<0xE3>），取值落空、剩下的字节还不是合法
    UTF-8。所以脚本里变量后面跟中文一律写 ${VAR}。这里钉住这个写法。"""
    r = subprocess.run(["sh", "-c", 'P=/tmp/x; printf "%s\\n" "A「${P}」B"'],
                       capture_output=True)
    assert r.stdout.decode("utf-8") == "A「/tmp/x」B\n", r.stdout.hex()


def test_no_bare_var_before_cjk():
    """静态守一遍：模板里不许出现 `$VAR` 紧跟非 ASCII。"""
    import re
    pat = re.compile(r"\$[A-Za-z0-9_]+[^\x00-\x7f]")
    bad = []
    with open(os.path.join(ROOT, "tools", "installer.sh"), encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if line.lstrip().startswith("#"):
                continue
            if pat.search(line):
                bad.append("%d: %s" % (i, line.strip()))
    assert not bad, "变量后面紧跟中文要写 ${VAR}：\n" + "\n".join(bad)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX 安装器")
def test_refuses_home_as_prefix(tool, src, tmp_path):
    out = str(tmp_path / "x.run")
    tool.build(src, "linux-x64", out)
    home = tmp_path / "home"
    home.mkdir()
    r = subprocess.run(["sh", out, "--yes", "--quiet", "--prefix", str(home)],
                       capture_output=True, env=dict(os.environ, HOME=str(home)))
    assert r.returncode != 0
    try:
        err = r.stderr.decode("utf-8")
    except UnicodeDecodeError as e:
        pytest.fail("stderr 不是合法 UTF-8：%s（%s）" % (r.stderr.hex(), e))
    assert "拒绝" in err


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX 安装器")
def test_installs_over_leftover_data(tool, src, tmp_path):
    """卸载会留下 状态/、persona.md，重装得能接着用。

    判据不能只是「目录非空就拒绝」—— 那样卸载过一次就再也装不回去了。
    """
    out = str(tmp_path / "x.run")
    tool.build(src, "linux-x64", out)
    home = tmp_path / "home"
    home.mkdir()
    app = home / "app"
    (app / "状态").mkdir(parents=True)
    (app / "状态" / "探针.txt").write_text("keep", encoding="utf-8")
    (app / "persona.md").write_text("我的", encoding="utf-8")

    r = subprocess.run(["sh", out, "--yes", "--quiet", "--prefix", str(app)],
                       capture_output=True, text=True,
                       env=dict(os.environ, HOME=str(home)))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (app / "pojia-ce").is_file()
    assert (app / "状态" / "探针.txt").read_text(encoding="utf-8") == "keep"
    assert (app / "persona.md").read_text(encoding="utf-8") == "我的"

# -*- coding: utf-8 -*-
"""打包参数：单文件版的解包目录不能再落回 %TEMP%。

这条参数的来由见 tools/build_exe.py 里的 runtime_tmpdir_for 注释 —— 落回
%TEMP% 的产物在部分机器上根本起不来，而失败点在 Python 之前，程序里做什么
都救不回来。所以只能靠打包期决定，也就在这里钉住。
"""

import importlib.util
import os
from types import SimpleNamespace

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def be():
    path = os.path.join(ROOT, "tools", "build_exe.py")
    spec = importlib.util.spec_from_file_location("_build_exe_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _args(onedir=False, tmpdir=None):
    return SimpleNamespace(onedir=onedir, runtime_tmpdir=tmpdir)


def test_windows_onefile_defaults_below_localappdata(be):
    """Windows 单文件版不给参数时，解包目录落在 LocalAppData 下。"""
    rt = be.runtime_tmpdir_for(_args(), nt=True)
    assert rt
    assert "%LOCALAPPDATA%" in rt
    assert "pojia-ce" in rt


def test_windows_onedir_needs_no_tmpdir(be):
    """目录形态不解包，给了参数也不该带进命令行。"""
    assert be.runtime_tmpdir_for(_args(onedir=True), nt=True) == ""


def test_explicit_tmpdir_wins(be):
    """显式指定的目录优先，不被默认值盖掉。"""
    assert be.runtime_tmpdir_for(_args(tmpdir=r"D:\rt"), nt=True) == r"D:\rt"


def test_posix_keeps_bootloader_default(be):
    """POSIX 的 bootloader 不展开环境变量，塞 %VAR% 进去等于给它一条坏路径。"""
    assert be.runtime_tmpdir_for(_args(), nt=False) == ""


def test_build_version_reads_core(be):
    """版本号从核心脚本里读，形态是 8.62-CE。"""
    v = be.build_version(be.CORE)
    assert v and v[0].isdigit() and "-" in v


def test_write_version_file_single_line(be, tmp_path):
    """落盘必须是一行纯版本号 —— 界面读第一行就直接拿去显示。"""
    dest = tmp_path / "nested" / "_version.txt"
    p = be.write_version_file(be.CORE, str(dest))
    assert p and os.path.isfile(p)
    lines = open(p, encoding="utf-8").read().splitlines()
    assert lines == [be.build_version(be.CORE)]

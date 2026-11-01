# -*- coding: utf-8 -*-
"""命令行冒烟测试：把脚本当黑盒跑一遍真实入口。

重点不是功能细节（那些在别的文件里测），而是「一台干净机器上跑起来会不会
炸」—— 缺文件、缺目录、非 Windows、locale 不是 UTF-8，这些只有真跑才会暴露。
所有子进程都换掉 HOME / APPDATA，绝不碰真实配置。
"""
import os
import subprocess
import sys

import pytest

from conftest import CORE_PATH


def make_env(tmp_path):
    """把用户目录相关环境变量全部指向临时目录。"""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    appdata = tmp_path / "appdata"
    appdata.mkdir(exist_ok=True)
    local = tmp_path / "localappdata"
    local.mkdir(exist_ok=True)

    env = dict(os.environ)
    env.update({
        "HOME": str(home),
        "USERPROFILE": str(home),
        "APPDATA": str(appdata),
        "LOCALAPPDATA": str(local),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUTF8": "1",
        # 别让子进程继承我们的 QUIET / 调试开关
        "PYTHONPATH": "",
    })
    return env, home


def run(args, env, timeout=240):
    return subprocess.run(
        [sys.executable, CORE_PATH] + args,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, stdin=subprocess.DEVNULL, timeout=timeout)


@pytest.fixture()
def clean_env(tmp_path):
    return make_env(tmp_path)


def test_version(core, clean_env):
    env, _home = clean_env
    r = run(["--version"], env)
    assert r.returncode == 0
    assert core.VER_TAG in r.stdout


def test_help_lists_every_target_and_dir_flag(core, clean_env):
    env, _home = clean_env
    r = run(["--help"], env)
    assert r.returncode == 0
    for key in core.DEFAULT_TARGETS:
        assert key in r.stdout, "--help 里没有目标 %s" % key
    assert "--kiro-dir" in r.stdout


def test_status_on_clean_machine(core, clean_env):
    """一台什么都没装的机器：要报「没检测到」，不能崩。"""
    env, _home = clean_env
    r = run(["--status", "--target", "kiro"], env)
    assert r.returncode == 0, r.stderr
    assert "Kiro" in r.stdout
    assert "没检测到" in r.stdout or "不存在" in r.stdout


def test_unknown_target_is_reported(clean_env):
    env, _home = clean_env
    r = run(["--status", "--target", "kiroooo"], env)
    assert "未知目标" in r.stdout


def test_check_runs_and_exits_clean(clean_env):
    env, _home = clean_env
    r = run(["--check"], env, timeout=300)
    assert r.returncode == 0, r.stderr
    assert "体检结论" in r.stdout


def test_apply_then_revert_via_cli(clean_env):
    """走真实入口打一遍再还原，确认文件系统上真的干净了。"""
    env, home = clean_env
    claude = home / ".claude"
    claude.mkdir()

    r = run(["--apply", "-y", "--target", "claude"], env)
    assert r.returncode == 0, r.stderr
    target = claude / "CLAUDE.md"
    assert target.is_file(), "apply 没建出 CLAUDE.md"
    txt = target.read_text(encoding="utf-8")
    assert "POJIA-NEXT-INJECT:BEGIN" in txt
    assert "POJIA-CE-MIRROR:BEGIN" in txt

    r = run(["--revert", "-y", "--target", "claude"], env)
    assert r.returncode == 0, r.stderr
    assert not target.exists(), "revert 后应删掉原本不存在的文件"


def test_dry_run_writes_nothing(clean_env):
    env, home = clean_env
    gemini = home / ".gemini"
    gemini.mkdir()

    r = run(["--apply", "--dry-run", "-y", "--target", "gemini"], env)
    assert r.returncode == 0, r.stderr
    assert not (gemini / "GEMINI.md").exists(), "预演居然落盘了"
    assert "预演" in r.stdout

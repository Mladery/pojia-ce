# -*- coding: utf-8 -*-
"""命令行入口：打包版（双击 exe）与被当成普通脚本跑时的行为差异。

这一组钉的是三个真实踩过的坑：

  · `exe --menu` 想看菜单，结果跑了一遍状态检测 —— 判交互只看了 argv 长度，
    --menu 既不算长度也不算动作，一路落到 run_status
  · 参数写错时只丢一行英文 `unrecognized arguments`，打包版双击的窗口一闪而过
  · 帮助里的示例把命令名写死成 `python 破甲一键通.py`，打包版用户以为要装 Python
"""
import os
import sys

import pytest


class A:
    """够用的 Namespace 替身。"""

    menu = False
    pause = False
    files = []

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ---------------------------------------------------------------- 交互判定

def test_no_args_is_interactive(core):
    assert core._want_interactive(A(), argc=1)


def test_menu_flag_is_interactive(core):
    """`exe --menu` 必须进菜单 —— 这是本轮修的 bug。"""
    assert core._want_interactive(A(menu=True), argc=2)


def test_action_is_not_interactive(core):
    assert not core._want_interactive(A(), argc=2)


def test_menu_flag_is_parsed(core):
    ns = core.build_parser().parse_args(["--menu"])
    assert ns.menu is True
    assert ns.files == []


# ---------------------------------------------------------------- 双击默认开界面

def test_double_click_opens_gui_when_frozen(core, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "argv", ["pojia-ce.exe"])
    assert core._default_to_gui(A()) is True


def test_menu_flag_suppresses_gui(core, monkeypatch):
    """打包版带 --menu 时不能又去开界面，否则菜单永远进不去。"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "argv", ["pojia-ce.exe", "--menu"])
    assert core._default_to_gui(A(menu=True)) is False


def test_source_mode_never_auto_gui(core, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "argv", ["破甲一键通.py"])
    assert core._default_to_gui(A()) is False


# ---------------------------------------------------------------- 命令名与帮助

def test_cmd_name_source_mode(core, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    assert core._cmd_name().startswith("python ")
    assert core._cmd_name().endswith("破甲一键通.py")


def test_cmd_name_frozen(core, monkeypatch):
    """打包版别再自称 `python xxx.py` —— 用户会以为得先装 Python。"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(core, "SELF", os.path.join("dist", "pojia-ce.exe"))
    assert core._cmd_name() == "pojia-ce.exe"


def test_epilog_uses_cmd_name(core, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(core, "SELF", os.path.join("dist", "pojia-ce.exe"))
    text = core._epilog()
    assert "pojia-ce.exe --menu" in text
    assert "python " not in text


def test_epilog_has_menu_example(core):
    """菜单是打包版的主要入口，帮助里必须有它。"""
    assert "--menu" in core._epilog()


# ---------------------------------------------------------------- 报错与留屏

def test_bad_flag_is_chinese_and_exit_2(core, capsys, monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)
    with pytest.raises(SystemExit) as ei:
        core.build_parser().parse_args(["--appply"])
    assert ei.value.code == 2
    out = capsys.readouterr().out
    assert "参数有问题" in out
    assert "认不出 --appply" in out
    assert "--help" in out


def test_help_holds_screen_only_when_frozen(core, capsys, monkeypatch):
    """冻结态 --help 要停一下（窗口是本进程独占的），源码态不停。"""
    calls = []
    monkeypatch.setattr(core, "_hold_screen", lambda: calls.append(1))

    monkeypatch.delattr(sys, "frozen", raising=False)
    with pytest.raises(SystemExit):
        core.build_parser().parse_args(["--help"])
    assert calls == []

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    with pytest.raises(SystemExit):
        core.build_parser().parse_args(["--version"])
    assert calls == [1]


def test_dropped_files_are_swallowed(core):
    """拖文件到 exe 图标上不该变成 unrecognized arguments。"""
    ns = core.build_parser().parse_args(["a.md", "b.txt"])
    assert ns.files == ["a.md", "b.txt"]


def test_pause_flag_parsed(core):
    assert core.build_parser().parse_args(["--status", "--pause"]).pause is True

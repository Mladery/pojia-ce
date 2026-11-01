# -*- coding: utf-8 -*-
"""测试公共装置。

核心脚本的文件名是中文（`破甲一键通.py`），直接 `import` 在部分环境里不稳
（尤其 CI 的 locale 不是 UTF-8 时），所以统一走 importlib 按路径加载，不依赖
包名。所有测试都只在临时目录里操作，**绝不碰真实的 ~**。
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
CORE_PATH = os.path.join(SRC, "破甲一键通.py")
GUI_PATH = os.path.join(SRC, "破甲GUI.py")
README_PATH = os.path.join(ROOT, "README.md")


def load_module(name, path):
    """按路径加载一个 .py，注册进 sys.modules 后返回模块对象。"""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def core():
    """核心脚本模块（整个会话只加载一次）。"""
    return load_module("pojia_core", CORE_PATH)


@pytest.fixture(scope="session")
def gui():
    """图形界面模块。只用来核对目标列表，不启动 UI。"""
    return load_module("pojia_gui", GUI_PATH)


class Args:
    """一个够用的 argparse.Namespace 替身。

    目标的 apply / revert 会 getattr 一堆开关，缺一个就 AttributeError，
    所以这里给全量默认值，测试里按需覆盖。
    """

    dry_run = False
    yes = True
    force = True
    diagnose = False
    kill_dsh = False
    persona = ""
    quiet = True

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


@pytest.fixture()
def args():
    return Args()


@pytest.fixture()
def userhome(tmp_path):
    """一个假的用户目录。"""
    h = tmp_path / "home"
    h.mkdir()
    return str(h)

# -*- coding: utf-8 -*-
"""安装根定位：新增的两个只读来源。

  ① 进程镜像路径 —— 以前的进程反查只解析命令行，壳把真 exe 藏进子进程参数时
     会指到父进程目录；镜像路径由内核记，改不了。
  ② 卸载登记表 —— 装到自定义盘符、又没建快捷方式时，安装器写进注册表的
     InstallLocation 是唯一还留着的书面记录。

这里钉住的是「读到之后怎么用」：向上找根、三种注册表值形态、命中来源标注。
"""
import os


def test_walk_up_to_root(core, tmp_path):
    root = tmp_path / "App"
    (root / "bin").mkdir(parents=True)
    judge = lambda d: os.path.basename(d) == "App"
    assert core._walk_up_to_root(str(root / "bin"), judge) == str(root)
    assert core._walk_up_to_root(str(tmp_path / "nope"), judge) == ""


def test_walk_up_stops_at_fs_root(core):
    """一路走到文件系统根还没命中就认输，不能把根目录当安装根返回。"""
    root = os.path.abspath(os.sep)        # Windows 是 C:\，POSIX 是 /
    assert core._walk_up_to_root(root, lambda d: True) == root
    assert core._walk_up_to_root(root, lambda d: False) == ""


def test_dir_of_install_value_forms(core, tmp_path):
    d = tmp_path / "inst"
    d.mkdir()
    exe = d / "app.exe"
    exe.write_text("x", encoding="utf-8")
    assert core._dir_of_install_value(str(d)) == str(d)
    assert core._dir_of_install_value('"%s",0' % exe) == str(d)
    assert core._dir_of_install_value('"%s" /S' % exe) == str(d)
    assert core._dir_of_install_value("") == ""
    assert core._dir_of_install_value("Z:\\nope") == ""


def test_find_install_via_uninstall(core, tmp_path, monkeypatch):
    root = tmp_path / "DSH Desktop"
    root.mkdir()
    monkeypatch.setattr(core, "_uninstall_entries",
                        lambda: [("无关软件", str(tmp_path)), ("DSH Desktop", str(root))])
    got = core.find_install_via_uninstall(("DSH Desktop.exe",),
                                          lambda d: os.path.basename(d) == "DSH Desktop")
    assert got == str(root)


def test_find_install_via_uninstall_ignores_unrelated(core, tmp_path, monkeypatch):
    monkeypatch.setattr(core, "_uninstall_entries", lambda: [("别的软件", str(tmp_path))])
    assert core.find_install_via_uninstall(("DSH Desktop.exe",), lambda d: True) == ""


def test_discover_app_root_labels_uninstall(core, tmp_path, monkeypatch):
    root = tmp_path / "DSH Desktop"
    root.mkdir()
    monkeypatch.setattr(core, "find_install_via_process", lambda exe, judge: "")
    monkeypatch.setattr(core, "find_install_via_switch", lambda exe, judge: "")
    monkeypatch.setattr(core, "find_install_via_shortcuts", lambda exe, judge: "")
    monkeypatch.setattr(core, "find_install_via_uninstall", lambda exes, judge: str(root))
    got, src = core.discover_app_root(("__pojia_test_exe__.exe",), lambda d: True, walk=False)
    assert got == str(root)
    assert src == "卸载登记表"


def test_proc_image_path_self(core):
    """自己这个进程的镜像路径：Windows 走 Kernel32，Linux 走 /proc，macOS 两条都没有。"""
    p = core._proc_image_path(os.getpid())
    if core.IS_WIN or os.path.isdir("/proc/self"):
        assert p and os.path.isabs(p)
    else:
        # 没有 procfs 的平台返回空，定位链自动退到命令行与快捷方式
        assert p == ""
    assert core._proc_image_path(-1) == ""

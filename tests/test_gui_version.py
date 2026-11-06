# -*- coding: utf-8 -*-
"""界面取版本号与退出留屏：两条都不许卡。

症状是图形界面停在横幅第一行、浏览器也不开。根因是界面冻结态为了显示版本号
起了一个 `exe --version` 子进程，那个子进程继承了终端的 stdin，退出前的留屏
逻辑在等一个没人按的回车 —— 父进程卡在 subprocess.run 里，连 HTTP 服务都没
起来（端口已 bind，但 accept 循环还没进）。

这里钉住两条：版本号从打包带上来的文件读；留屏只在两头都挂着真终端时生效。
"""

import sys


def _tty(value):
    class _Stream:
        def isatty(self):
            return value

    return _Stream()


def test_version_read_from_packaged_file(gui, tmp_path, monkeypatch):
    """有 _version.txt 就直接读，一次子进程都不起。"""
    (tmp_path / "_version.txt").write_text("8.62-CE\n", encoding="utf-8")
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(gui, "_VER_CACHE", [], raising=False)

    def _no_spawn(*a, **kw):
        raise AssertionError("不该为了一行版本号起子进程")

    monkeypatch.setattr(gui.subprocess, "run", _no_spawn)
    assert gui._frozen_version() == "8.62-CE"


def test_version_uses_cache_when_warm(gui, tmp_path, monkeypatch):
    """缓存命中就不再读盘 —— 一次会话只问一遍。"""
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(gui, "_VER_CACHE", ["9.99-CE"], raising=False)
    assert gui._frozen_version() == "9.99-CE"


def test_hold_screen_skips_when_stdout_is_piped(core, monkeypatch):
    """stdout 被管道接走时不停 —— 界面问版本号时子进程就是这个处境。"""
    calls = []
    monkeypatch.setattr(sys, "stdin", _tty(True))
    monkeypatch.setattr(sys, "stdout", _tty(False))
    monkeypatch.setattr("builtins.input", lambda *a: calls.append(a))
    core._hold_screen()
    assert calls == []


def test_hold_screen_waits_in_real_terminal(core, monkeypatch):
    """两头都挂在终端上才停一次，双击运行的场景靠的就是这次停留。"""
    calls = []
    monkeypatch.setattr(sys, "stdin", _tty(True))
    monkeypatch.setattr(sys, "stdout", _tty(True))
    monkeypatch.setattr("builtins.input", lambda *a: calls.append(a))
    core._hold_screen()
    assert len(calls) == 1


def test_check_update_parses_core_output(gui, monkeypatch):
    """界面不自己算版本：跑一次 --check-update，把那一行读懂就行。"""
    class R:
        stdout = "  最新发布：8.70　当前：8.63\n  有新版本。升级：pojia-ce --update\n".encode()

    monkeypatch.setattr(gui.subprocess, "run", lambda *a, **k: R())
    d = gui.check_update()
    assert d["ok"] and d["newer"]
    assert (d["latest"], d["current"]) == ("8.70", "8.63")


def test_check_update_reports_up_to_date(gui, monkeypatch):
    class R:
        stdout = "  最新发布：8.63　当前：8.63\n  已是最新\n".encode()

    monkeypatch.setattr(gui.subprocess, "run", lambda *a, **k: R())
    d = gui.check_update()
    assert d["ok"] and not d["newer"]


def test_check_update_reports_failure(gui, monkeypatch):
    """查不到不算「没有新版」——ok=False 时界面什么条都不亮。"""
    class R:
        stdout = "  检查更新失败：no route\n".encode()

    monkeypatch.setattr(gui.subprocess, "run", lambda *a, **k: R())
    assert gui.check_update()["ok"] is False


def test_install_button_maps_to_update_flag(gui):
    """「安装」按钮最终就是一条 --update；界面自己不做下载。"""
    assert gui.build_cmd("update", [])[-1] == "--update"


def test_page_has_install_banner(gui):
    page = gui.render_page()
    assert 'id="u-bar"' in page and 'id="u-go"' in page
    assert "/api/update" in page            # 只读检查的入口
    assert 'run("update")' in page          # 按钮走同一个 run()

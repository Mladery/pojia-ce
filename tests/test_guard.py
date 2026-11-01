# -*- coding: utf-8 -*-
"""DSH 运行时守卫（pojia-ce-guard）的安装 / 状态 / 卸载。

这一层要往用户的 DSH 配置目录里写三处东西，写坏了 DSH 就起不来，
所以每一条都验：装得上、装两次不多写、卸完跟原来一模一样。
"""
import json
import os
import shutil
import subprocess

import pytest


@pytest.fixture()
def dsh_home(tmp_path):
    """一个最小可用的 DSH 桌面版布局：profiles/desktop + 两个配置文件。"""
    prof = tmp_path / ".dsh" / "profiles" / "desktop"
    prof.mkdir(parents=True)
    (prof / "cordis.patch.yml").write_text(
        "- id: someone-else\n  name: 'someone-else'\n", encoding="utf-8")
    (prof / "package.json").write_text(
        json.dumps({"name": "desktop", "dependencies": {"other": "1.0.0"}},
                   indent=2) + "\n", encoding="utf-8")
    return str(tmp_path / ".dsh")


def _guard_pkg(dsh_home, core):
    return os.path.join(dsh_home, "profiles", "desktop", "node_modules",
                        core.GUARD_ID)


def test_guard_install_writes_three_places(core, dsh_home):
    ok, note = core.guard_install(dsh_home)
    assert ok, note

    pkg = _guard_pkg(dsh_home, core)
    assert os.path.isfile(os.path.join(pkg, "package.json"))
    assert os.path.isfile(os.path.join(pkg, "index.js"))

    prof = os.path.join(dsh_home, "profiles", "desktop")
    yml = open(os.path.join(prof, "cordis.patch.yml"), encoding="utf-8").read()
    assert ("id: " + core.GUARD_ID) in yml
    assert "someone-else" in yml, "别人的条目被删了"

    deps = json.load(open(os.path.join(prof, "package.json"), encoding="utf-8"))["dependencies"]
    assert deps[core.GUARD_ID] == core.GUARD_DEP
    assert deps["other"] == "1.0.0"


def test_guard_install_is_idempotent(core, dsh_home):
    core.guard_install(dsh_home)
    prof = os.path.join(dsh_home, "profiles", "desktop")
    before = open(os.path.join(prof, "cordis.patch.yml"), encoding="utf-8").read()

    ok, note = core.guard_install(dsh_home)
    assert ok
    assert "已就位" in note
    after = open(os.path.join(prof, "cordis.patch.yml"), encoding="utf-8").read()
    assert before == after, "重装把配置又写了一遍"


def test_guard_remove_restores_original(core, dsh_home):
    prof = os.path.join(dsh_home, "profiles", "desktop")
    yml0 = open(os.path.join(prof, "cordis.patch.yml"), encoding="utf-8").read()
    pj0 = json.load(open(os.path.join(prof, "package.json"), encoding="utf-8"))

    core.guard_install(dsh_home)
    ok, note = core.guard_remove(dsh_home)
    assert ok, note

    assert open(os.path.join(prof, "cordis.patch.yml"), encoding="utf-8").read() == yml0
    assert json.load(open(os.path.join(prof, "package.json"), encoding="utf-8")) == pj0
    assert not os.path.isdir(_guard_pkg(dsh_home, core))


def test_guard_rows_reflect_state(core, dsh_home):
    assert core.guard_rows(dsh_home)[0][0] == "info"

    core.guard_install(dsh_home)
    assert core.guard_rows(dsh_home)[0][0] == "ok"

    # 只删插件目录 → 半安装，必须报出来而不是当没事
    shutil.rmtree(_guard_pkg(dsh_home, core))
    assert core.guard_rows(dsh_home)[0][0] == "warn"


def test_guard_absent_profile_is_not_an_error(core, tmp_path):
    """没有 profiles/desktop（非桌面版布局）时不能报错，只能跳过。"""
    rows = core.guard_rows(str(tmp_path))
    assert rows and rows[0][0] == "dg"
    ok, note = core.guard_install(str(tmp_path))
    assert not ok and "profiles/desktop" in note


def test_guard_js_has_no_upstream_version(core):
    """插件里不许出现上游的版本号 —— 那是逆向来源的指纹。"""
    for bad in ("8.26", "8.27", "8.28", "8.29"):
        assert bad not in core.GUARD_JS
        assert bad not in core.GUARD_PKG


def test_guard_js_is_valid_esm(core, tmp_path):
    """用 node --check 过一遍语法。没装 node 就跳过（CI 上一般都有）。"""
    node = shutil.which("node")
    if not node:
        pytest.skip("没有 node，跳过语法检查")

    p = tmp_path / "guard.mjs"
    p.write_text(core.GUARD_JS, encoding="utf-8")
    r = subprocess.run([node, "--check", str(p)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_guard_js_exports_cordis_contract(core):
    """Cordis 插件的契约：具名导出 name + apply，缺一个就加载不起来。"""
    js = core.GUARD_JS
    assert 'export const name = "%s"' % core.GUARD_ID in js
    assert "export function apply(ctx, config)" in js
    assert '"agent/status"' in js
    assert "agent.followup(" in js

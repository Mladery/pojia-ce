# -*- coding: utf-8 -*-
"""还原彻底性：痕迹清理 + 原档保险库。

"补丁还原了、盘上还留着我们动过的东西"就是用户报的"还原不彻底"。这里逐项钉住：
解包目录、自建备份、专属目录、保险丝，以及旁路备份丢了之后的兜底。
"""
import hashlib
import os
import shutil

import pytest


@pytest.fixture()
def layout(tmp_path, monkeypatch):
    """一套桌面端布局 + 一个 DSH_HOME。"""
    root = tmp_path / "inst"
    res = root / "resources"
    app = res / "app" / "dsh" / "node_modules" / "@deepseek-ai"
    app.mkdir(parents=True)
    (app / "dsh-web-app").mkdir()
    (res / "app.asar").write_bytes(b"asar")
    base = str(app)
    home = tmp_path / "dsh"
    prof = home / "profiles" / "desktop"
    prof.mkdir(parents=True)
    (prof / "cordis.patch.yml").write_text("- id: x\n", encoding="utf-8")
    monkeypatch.setenv("DSH_HOME", str(home))   # dsh_home() 认这个变量
    return str(root), str(res), base, str(home), prof


def test_traces_delete_marked_unpack(core, layout):
    _root, res, base, home, _prof = layout
    app = os.path.join(res, "app")
    open(os.path.join(app, core.DshTarget._ASAR_MARK), "w", encoding="utf-8").write("{}")
    acts = core.revert_traces(home, [base])
    assert any(k == "解包目录" for k, _ in acts)
    assert not os.path.isdir(app)


def test_traces_keep_unmarked_unpack_by_default(core, layout):
    _root, res, base, home, _prof = layout
    app = os.path.join(res, "app")
    acts = core.revert_traces(home, [base])
    assert os.path.isdir(app), "没有标记的 app/ 可能是用户自己解的，默认不能删"
    assert any(k.startswith("待确认") for k, _ in acts)


def test_traces_delete_unmarked_unpack_with_deep(core, layout):
    _root, res, base, home, _prof = layout
    app = os.path.join(res, "app")
    acts = core.revert_traces(home, [base], deep=True)
    assert any("--deep" in k for k, _ in acts)
    assert not os.path.isdir(app)


def test_traces_remove_our_backups_and_dir(core, layout):
    _root, res, base, home, prof = layout
    bak = prof / "cordis.patch.yml.pojia-preset.bak"
    bak.write_text("x", encoding="utf-8")
    keep = prof / "cordis.patch.yml.bak-20260101-000000"
    keep.write_text("x", encoding="utf-8")
    md = core.avatar_dir_for(home)
    os.makedirs(md, exist_ok=True)
    (prof / "package.json").write_text("{}", encoding="utf-8")

    core.revert_traces(home, [base])
    assert not bak.exists()
    assert keep.exists(), "别人的备份不能碰"
    assert not os.path.isdir(md)


def test_traces_dry_run_changes_nothing(core, layout):
    _root, res, base, home, prof = layout
    app = os.path.join(res, "app")
    open(os.path.join(app, core.DshTarget._ASAR_MARK), "w", encoding="utf-8").write("{}")
    bak = prof / "x.pojia-guard.bak"
    bak.write_text("x", encoding="utf-8")
    md = core.avatar_dir_for(home)
    os.makedirs(md, exist_ok=True)

    acts = core.revert_traces(home, [base], dry=True)
    assert acts, "预演也要列出会清什么"
    assert os.path.isdir(app) and bak.exists() and os.path.isdir(md)


def test_vault_roundtrip(core, layout):
    _root, _res, _base, home, _prof = layout
    fp = os.path.join(home, "target.js")
    with open(fp, "wb") as f:
        f.write(b"original")
    out = core.vault_put(home, fp)
    assert out and os.path.isfile(out)
    assert core.vault_get(home, fp) == b"original"
    assert core.vault_count(home) == 1


def test_sha1_survives_python38(core, layout, monkeypatch):
    """Python 3.8 的 hashlib.sha1 不认 usedforsecurity 关键字，不能因此静默失效。

    这条是真踩过的：`_vault_key` 直接把关键字传下去，3.8 上抛 TypeError，被
    `vault_put` 的 `except Exception` 吞掉 → 返回 ""，保险库里空空如也，还原时
    取不到原档，一路静默降级成 nobak。CI 的 3.8 任务就是这么红的。
    """
    _root, _res, _base, home, _prof = layout
    real = hashlib.sha1

    def fake(data=b"", **kw):
        if kw:                                   # 模拟 3.8：只吃一个位置参数
            raise TypeError("openssl_sha1() takes at most 1 argument (2 given)")
        return real(data)

    monkeypatch.setattr(hashlib, "sha1", fake)
    assert len(core._sha1(b"x").hexdigest()) == 40

    fp = os.path.join(home, "t.js")
    with open(fp, "wb") as f:
        f.write(b"original")
    assert core.vault_put(home, fp), "3.8 上保险库不能静默失效"
    assert core.vault_get(home, fp) == b"original"
    assert core.file_sha16(fp)


def test_revert_uses_vault_when_backup_missing(core, layout):
    _root, _res, _base, home, _prof = layout
    t = core.DshTarget()
    fp = os.path.join(home, "target.js")
    with open(fp, "wb") as f:
        f.write(b"original")
    core.vault_put(home, fp)
    # 模拟：补丁写进去了，旁路备份被清理工具删掉
    with open(fp, "wb") as f:
        f.write(b"patched-by-us")
    assert not os.path.exists(fp + ".dshpurge.bak")
    assert t.revert_file(fp) == "vault"
    with open(fp, "rb") as f:
        assert f.read() == b"original"


def test_revert_reports_nobak_without_vault(core, layout):
    _root, _res, _base, home, _prof = layout
    t = core.DshTarget()
    fp = os.path.join(home, "target.js")
    with open(fp, "wb") as f:
        f.write(b"patched-by-us")
    assert t.revert_file(fp) == "nobak"


def test_revert_stamp_roundtrip(core, layout):
    _root, _res, _base, home, _prof = layout
    root = os.path.join(home, "inst")
    asar = os.path.join(root, "resources", "app.asar")
    os.makedirs(os.path.dirname(asar), exist_ok=True)
    with open(asar, "wb") as f:
        f.write(b"asar-bytes")
    assert core.revert_stamp_hit(root, asar, home) is False
    assert core.revert_stamp_mark(root, asar, home) is True
    assert core.revert_stamp_hit(root, asar, home) is True
    # asar 换过（宿主升级）就不算数了
    with open(asar, "wb") as f:
        f.write(b"asar-bytes-new-version")
    assert core.revert_stamp_hit(root, asar, home) is False
    core.revert_stamp_clear(root, home)
    assert core.revert_stamp_load(home) == {}


def test_stamp_blocks_auto_unpack(core, layout):
    """还原过就别再自动解包 —— 否则删掉的 resources/app/ 会被下一次体检解回来。"""
    _root, res, _base, _home, _prof = layout
    root = os.path.dirname(os.path.abspath(res))
    asar = os.path.join(res, "app.asar")
    assert core.revert_stamp_mark(root, asar) is True
    shutil.rmtree(os.path.join(res, "app"), ignore_errors=True)   # 还原时已经删了
    core.DshTarget._unpack_ok = False
    try:
        assert core.DshTarget.asar_extract_agent_dir(res) == ""
        assert not os.path.isdir(os.path.join(res, "app"))
    finally:
        core.DshTarget._unpack_ok = True
        core.revert_stamp_clear(root)

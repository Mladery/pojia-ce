# -*- coding: utf-8 -*-
"""Kiro 按 Claude 处理 + 三处 Kiro 独有的差异。

Kiro 是 AWS 的 agentic IDE，底层模型就是 Claude —— 所以 CLAUDE_ADDENDUM
原样挂上。多出来的 KIRO_ADDENDUM 只处理三件 Claude Code 没有的事：
steering 整目录全量加载、Supervised 模式下的工具审批 Deny、spec 流程。
"""
import os

from conftest import Args


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _lf(text):
    return text.replace("\r\n", "\n")


def test_kiro_gets_claude_sections(core):
    text = _lf(core.build_persona_text("", "Kiro", "kiro"))

    # 工具型执行纪律 + Claude 那六条 + Kiro 自己那四条
    assert core.CODING_AGENT_ADDENDUM in text
    assert core.CLAUDE_ADDENDUM in text
    assert core.KIRO_ADDENDUM in text
    # 别家的段不能串过来
    assert core.GLM_ADDENDUM not in text


def test_kiro_section_covers_three_real_differences(core):
    text = core.KIRO_ADDENDUM
    # 底层是 Claude，这一点必须写在最前面（否则模型会以为换了一套规则）
    assert "底层模型是 Claude" in text
    # Supervised 模式的 Deny 不是"被规则拒绝"
    assert "Supervised" in text and "Deny" in text
    # steering 全量加载：别人的工程约定不是判定规则
    assert "steering" in text and "不是判定规则" in text
    # spec 流程不能变成拖延
    assert "spec" in text and "tasks" in text
    # 边界仍是两条，不能在这里长第三条
    assert "两条边界" in text


def test_kiro_section_only_on_kiro(core):
    for key in ("codex", "claude", "zcode", "cursor", ""):
        assert core.KIRO_ADDENDUM not in _lf(core.build_persona_text("", "X", key))


def test_kiro_apply_writes_sections(core, tmp_path, monkeypatch):
    home = tmp_path / ".kiro"
    (home / "steering").mkdir(parents=True)
    t = core.KiroTarget()
    monkeypatch.setattr(t, "resolve_home", lambda _e="": str(home))

    t.apply(Args(kiro_dir=str(home)), "apply")

    txt = _lf(_read(os.path.join(str(home), core.KiroTarget.prompt_file)))
    assert core.CLAUDE_ADDENDUM in txt
    assert "Kiro 专用" in txt
    # 自证段仍在正文最后（专用段不能把它挤到中间），镜像块收在外面
    assert core.SIGNAL_REPLY in txt
    assert txt.index("Kiro 专用") < txt.index(core.SIGNAL_REPLY) < txt.index(core.MIRROR_END)

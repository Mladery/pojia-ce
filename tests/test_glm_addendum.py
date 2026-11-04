# -*- coding: utf-8 -*-
"""ZCode 的 GLM 专用正文。

GLM 和 Codex / Claude 的坏法不同：它会在思考通道里复述别家的对齐条款，
还会把自己当成 Claude 来拒绝。这一段就是冲这两点写的，所以测试要钉住
三件事：只挂 zcode、跟工具型段一起挂、其余目标一个字节都不变。
"""
import os

from conftest import Args


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _lf(text):
    return text.replace("\r\n", "\n")


def test_glm_section_only_on_zcode(core):
    base = core.build_persona_text("", "X")
    zc = _lf(core.build_persona_text("", "ZCode", "zcode"))

    assert core.GLM_ADDENDUM in zc
    # 工具型执行纪律也应当挂上（ZCode 同样带工具）
    assert core.CODING_AGENT_ADDENDUM in zc
    # 别家的专用段不能串到 GLM 上
    assert core.CLAUDE_ADDENDUM not in zc

    for key in ("codex", "claude"):
        assert core.GLM_ADDENDUM not in _lf(core.build_persona_text("", "X", key))
    # 其余目标逐字不变
    for key in ("cursor", "gemini", "qwen", ""):
        assert core.build_persona_text("", "X", key) == base


def test_glm_section_keeps_the_two_boundaries(core):
    """段里引用的边界必须仍是两条，不能在这里偷偷长出第三条。"""
    text = core.GLM_ADDENDUM
    assert "两条边界" in text
    assert "第 2 条" in text
    assert "第 3 条" not in text and "第三条" not in text


def test_zcode_apply_writes_glm_section(core, tmp_path, monkeypatch):
    home = tmp_path / ".zcode-ai"
    home.mkdir()
    t = core.ZCodeTarget()
    monkeypatch.setattr(t, "locate", lambda _a: (str(home), ""))
    monkeypatch.setattr(t, "default_skill_source", lambda: "")

    t.apply(Args(zcode_dir=str(home), zpatch=False), "apply")

    txt = _lf(_read(os.path.join(str(home), core.ZCODE_AGENTS)))
    assert "GLM 专用" in txt
    assert core.GLM_ADDENDUM in txt
    # 自证段仍在最后（专用段不能把兜底挤掉）
    assert txt.rstrip().endswith(core.SIGNAL_REPLY)

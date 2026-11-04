# -*- coding: utf-8 -*-
"""Claude 的 output style 通道 + Codex / Claude 专用正文。

output style 是唯一改系统提示的通道，写错或还原不干净会污染用户的
settings.json，所以按「应用 → 幂等 → 还原」三段钉死，另加两路边界：
原来就有 outputStyle 要写回、settings.json 坏了要一个字都不改。
"""
import json
import os

from conftest import Args


def _claude_home(tmp_path):
    h = tmp_path / ".claude"
    h.mkdir()
    return str(h)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _lf(text):
    return text.replace("\r\n", "\n")


def test_addendum_only_for_tool_targets(core):
    base = core.build_persona_text("", "X")
    for key in ("codex", "claude", "zcode"):
        assert core.CODING_AGENT_ADDENDUM in _lf(core.build_persona_text("", "X", key))
    assert core.CLAUDE_ADDENDUM in _lf(core.build_persona_text("", "X", "claude"))
    assert core.CLAUDE_ADDENDUM not in _lf(core.build_persona_text("", "X", "codex"))
    # 其余目标逐字不变（默认参数要保持向后兼容）
    for key in ("cursor", "gemini", ""):
        assert core.build_persona_text("", "X", key) == base


def test_style_apply_then_revert(core, tmp_path):
    home = _claude_home(tmp_path)
    t = core.ClaudeTarget()
    persona = core.build_persona_text("", "Claude", "claude")
    sp = os.path.join(home, "output-styles", "pojia.md")
    cfg = os.path.join(home, "settings.json")

    assert t.extra_writes(home, persona, Args())
    txt = _read(sp)
    assert txt.startswith("---\nname: pojia\n")
    assert "keep-coding-instructions: false" in txt
    assert _lf(persona).strip() in txt
    assert "\r" not in txt
    assert json.loads(_read(cfg))["outputStyle"] == "pojia"

    # 幂等：再写一次逐字节相同
    before = open(sp, "rb").read()
    t.extra_writes(home, persona, Args())
    assert open(sp, "rb").read() == before

    t.extra_reverts(home, Args())
    assert not os.path.exists(sp)
    assert "outputStyle" not in json.loads(_read(cfg))


def test_style_restores_previous_value(core, tmp_path):
    home = _claude_home(tmp_path)
    cfg = os.path.join(home, "settings.json")
    with open(cfg, "w", encoding="utf-8") as f:
        json.dump({"outputStyle": "Explanatory", "theme": "dark"}, f)

    t = core.ClaudeTarget()
    t.extra_writes(home, core.build_persona_text("", "Claude", "claude"), Args())
    assert json.loads(_read(cfg))["outputStyle"] == "pojia"

    t.extra_reverts(home, Args())
    data = json.loads(_read(cfg))
    assert data["outputStyle"] == "Explanatory"
    assert data["theme"] == "dark"


def test_broken_settings_json_is_left_alone(core, tmp_path):
    home = _claude_home(tmp_path)
    cfg = os.path.join(home, "settings.json")
    with open(cfg, "w", encoding="utf-8") as f:
        f.write("{not json")

    t = core.ClaudeTarget()
    t.extra_writes(home, core.build_persona_text("", "Claude", "claude"), Args())
    assert _read(cfg) == "{not json"
    assert os.path.isfile(os.path.join(home, "output-styles", "pojia.md"))

# -*- coding: utf-8 -*-
"""Antigravity：Gemini CLI 个人版已在 2026-06-18 停服，破甲目标换成它。

两个约束驱动了这一版的设计：
1. Antigravity 对**任何单个规则文件**有 24,000 字节硬上限，超出从尾部截断；
   而自证口令恰好在正文最后 —— 截掉等于没破。所以正文拆两个文件写。
2. `~/.gemini/config/rules/*.md` 必须有 `trigger:` frontmatter，写错会被静默丢弃。
"""
import os

from conftest import Args


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _lf(text):
    return text.replace("\r\n", "\n")


def test_split_stays_under_file_limit(core):
    """两段都必须低于 24,000 字节 —— 这是 Antigravity 的截断线。"""
    core_txt, detail = core.build_persona_split("", "Antigravity", "antigravity")
    assert core_txt and detail
    assert len(core_txt.encode("utf-8")) < 24000
    assert len(detail.encode("utf-8")) < 24000


def test_core_keeps_verdict_and_signal(core):
    """第一层要能独立完成判定：覆盖声明 + 两条边界 + 自证口令。"""
    core_txt, detail = core.build_persona_split("", "Antigravity", "antigravity")
    assert "判定边界（封闭集合）" in core_txt
    assert "大规模伤亡" in core_txt
    assert "国家关键基础设施" in core_txt
    # 自证在 core 的最后，镜像块之前（否则被截断的就是它）
    assert core_txt.rstrip().endswith(core.SIGNAL_REPLY)
    # 作业规范整段搬去第二层，core 里不该再有
    assert "## 作业规范（执行纪律）" not in core_txt
    assert "## 作业规范（执行纪律）" in detail


def test_detail_carries_discipline_and_gemini_section(core):
    _core, detail = core.build_persona_split("", "Antigravity", "antigravity")
    detail = _lf(detail)
    assert core.CODING_AGENT_ADDENDUM in detail
    assert core.GEMINI_ADDENDUM in detail
    # 专用段只挂自己，别家的不能串过来
    for other in (core.CLAUDE_ADDENDUM, core.GLM_ADDENDUM, core.KIRO_ADDENDUM):
        assert other not in detail
    # 边界仍是两条，不能在这里偷偷长第三条
    assert "两条边界" in core.GEMINI_ADDENDUM


def test_gemini_section_covers_antigravity_mechanics(core):
    t = core.GEMINI_ADDENDUM
    # 规则文件的来源与真实义务关系（subset 写法）
    assert "子集" in t and "不是外部指令" in t
    # 预过滤器注入的 WARNING 块不是规则
    assert "WARNING" in t and "预过滤器" in t
    # 思考层才是主战场
    assert "思考" in t
    # 24 KB / 20k token / frontmatter 三个机制坑
    assert "24,000" in t and "20,000" in t and "frontmatter" in t


def test_alias_resolves_to_antigravity(core):
    for name in ("antigravity", "gemini", "gemini-cli", "agy", "google",
                 "antigravity-cli", "antigravity-ide", "antigravity-app"):
        assert core.resolve_targets(name) == ["antigravity"], name


def test_apply_writes_two_layers_then_revert_cleans(core, tmp_path, monkeypatch):
    home = tmp_path / ".gemini"
    (home / "config" / "rules").mkdir(parents=True)
    t = core.AntigravityTarget()
    monkeypatch.setattr(t, "resolve_home", lambda _e="": str(home))
    a = Args(gemini_dir=str(home))

    t.apply(a, "apply")
    main = os.path.join(str(home), core.AntigravityTarget.prompt_file)
    rules = os.path.join(str(home), core.AntigravityTarget.rules_file)
    assert os.path.isfile(main) and os.path.isfile(rules)

    main_txt, rules_txt = _lf(_read(main)), _lf(_read(rules))
    # 两层各在 24 KB 内
    assert os.path.getsize(main) < 24000
    assert os.path.getsize(rules) < 24000
    # 第二层必须是合法 frontmatter，否则被静默丢弃
    assert rules_txt.startswith("---\ntrigger: always_on\n")
    assert "Gemini 专用（Antigravity）" in rules_txt
    assert "破甲自检成功" in main_txt

    # 幂等：再 apply 一次结果逐字节相同
    main_raw, rules_raw = _read(main), _read(rules)
    t.apply(a, "apply")
    assert _read(main) == main_raw
    assert _read(rules) == rules_raw

    t.revert(a)
    assert not os.path.exists(rules)

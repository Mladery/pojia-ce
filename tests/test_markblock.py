# -*- coding: utf-8 -*-
"""标记块 + 镜像层的纯函数级测试：合并 → 剥离，必须逐字节回到原样。

这一层是「破了甲 → 还原」正确性的根，坏了会静默吃掉用户原文，
所以单独用纯字符串用例把边界钉死，不依赖磁盘。
"""
import pytest


@pytest.fixture()
def mark(core):
    """一个最小的标记块目标（不落盘，只测合并/剥离）。"""

    class T(core._MarkBlockTarget):
        key = "t"
        label = "TEST"
        home_name = "testhome"
        prompt_file = "AGENTS.md"
        bak_suffix = ".bak"
        env_vars = ()

        def resolve_pick(self, path):
            return path, ""

        def pick_title(self):
            return ""

        def pick_hint(self):
            return ""

    return T()


def strip_all(t, text):
    """按 revert 的顺序剥：先主块，再镜像块。"""
    out = t._strip_block(text, t.mark_begin, t.mark_end)
    if t.mirror_begin:
        out = t._strip_block(out, t.mirror_begin, t.mirror_end)
    return out


def test_merge_adds_both_layers(mark, core):
    new = mark._merge("/tmp", "用户自己的内容\n第二行\n", "PERSONA-BODY")
    assert core.MIRROR_BEGIN in new
    assert mark.mark_begin in new
    assert "PERSONA-BODY" in new
    assert "用户自己的内容" in new


def test_roundtrip_restores_original(mark):
    orig = "用户自己的内容\n第二行\n"
    new = mark._merge("/tmp", orig, "PERSONA-BODY")
    back = strip_all(mark, new)
    assert back.strip() == orig.strip()


def test_roundtrip_empty_file(mark):
    new = mark._merge("/tmp", "", "PERSONA-BODY")
    back = strip_all(mark, new)
    assert back.strip() == ""


def test_second_merge_is_idempotent(mark, core):
    """二次 apply 必须是「替换」，不是「叠加」。"""
    one = mark._merge("/tmp", "用户内容\n", "PERSONA-V1")
    two = mark._merge("/tmp", one, "PERSONA-V2")
    assert two.count(mark.mark_begin) == 1, "主块被重复叠加"
    assert two.count(core.MIRROR_BEGIN) == 1, "镜像层被重复叠加"
    assert "PERSONA-V1" not in two and "PERSONA-V2" in two


def test_mirror_only_file_self_heals(mark, core):
    """主块被客户端吃掉、只剩镜像层时，apply 要能补回双层。"""
    text = "用户内容\n\n" + mark._mirror_block("")
    assert mark._has_mirror(text) and not mark._has_mark(text)
    healed = mark._merge("/tmp", text, "PERSONA-BODY")
    assert healed.count(mark.mark_begin) == 1
    assert healed.count(core.MIRROR_BEGIN) == 1


def test_mirror_only_file_strips_clean(mark):
    text = "用户内容\n\n" + mark._mirror_block("")
    assert strip_all(mark, text).strip() == "用户内容"


def test_codex_toml_has_no_mirror_layer(core):
    """config.toml 是结构化配置，镜像块只能落在它指向的指令文件里。"""
    assert core.CodexTarget().mirror_begin is None
    assert core.CodexTarget().mirror_end is None


def test_mirror_block_is_shorter_than_main(core):
    """镜像层的设计前提是「短」—— 长了就挤不进上下文热区，白加。"""
    user, _src = core.load_user_persona("")
    mt = core.build_mirror_text(user, "DSH")
    pt = core.build_persona_text(user, "DSH")
    assert mt.strip()
    assert len(mt) < len(pt) / 2


def test_mirror_carries_pass_block(core):
    """镜像层必须自带自证口令，否则「第二重申」只是重复一遍政策。"""
    user, _src = core.load_user_persona("")
    mt = core.build_mirror_text(user, "DSH")
    assert "破甲自检" in mt

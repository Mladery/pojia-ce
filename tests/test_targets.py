# -*- coding: utf-8 -*-
"""目标注册表的一致性检查。

这一组是「加目标时最容易漏的那几处」的守门员：
  · 目标加进 TARGETS 但没进 DEFAULT_TARGETS → --target all 里没有它
  · 有 arg_name 却没注册 --<key>-dir → 提示里写着能用，敲了报 unrecognized arguments
  · GUI 的 TARGETS 是另一份硬编码列表 → GUI 里选不到
  · TARGET_LABEL 缺项 → 横幅拼字符串时 KeyError
后两条都真踩过，所以钉成测试。
"""
import pytest


def test_registry_is_consistent(core):
    keys = set(core.TARGETS)
    assert set(core.DEFAULT_TARGETS) == keys, "DEFAULT_TARGETS 与 TARGETS 不一致"
    assert set(core.TARGET_LABEL) == keys, "TARGET_LABEL 与 TARGETS 不一致"


def test_no_duplicate_targets(core):
    assert len(core.DEFAULT_TARGETS) == len(set(core.DEFAULT_TARGETS))


def test_aliases_point_to_real_targets(core):
    bad = {a: t for a, t in core.TARGET_ALIAS.items()
           if t != "all" and t not in core.TARGETS}
    assert not bad, "别名指向不存在的目标：%s" % bad


def test_every_target_has_required_attrs(core):
    for key, cls in core.TARGETS.items():
        for attr in ("label", "key"):
            assert getattr(cls, attr, None), "%s 缺 %s" % (key, attr)
        assert cls.key == key, "%s 的 key 属性写成了 %s" % (key, cls.key)


def test_every_dir_arg_is_registered(core):
    """`--<key>-dir` 必须真的在 argparse 里 —— 这是曾经的 bug：

    十个目标在提示文案里写着「装了就用 --cline-dir 指定」，argparse 里根本没注册，
    用户照着敲只会得到 unrecognized arguments。越按提示走越进不去。
    """
    parser = core.build_parser()
    opts = set()
    for a in parser._actions:
        for o in a.option_strings:
            opts.add(o)

    missing = []
    for key in core.DEFAULT_TARGETS:
        arg_name = getattr(core.TARGETS[key], "arg_name", "")
        if not arg_name:
            continue
        flag = "--" + arg_name.replace("_", "-")
        if flag not in opts:
            missing.append("%s（%s）" % (flag, key))
    assert not missing, "这些目录参数没注册：%s" % "、".join(missing)


def test_parser_accepts_every_target_flag(core):
    """`--target kiro` 这类调用必须能被解析，不能只认一部分。"""
    parser = core.build_parser()
    for key in core.DEFAULT_TARGETS:
        ns = parser.parse_args(["--status", "--target", key])
        assert ns.target == key


def test_gui_target_list_matches_core(core, gui):
    """GUI 那份是独立硬编码的，不同步就等于 GUI 里选不到新目标。"""
    gui_keys = [k for k, _label in gui.TARGETS]
    assert gui_keys == core.DEFAULT_TARGETS, (
        "GUI 目标列表与核心不一致：\n  GUI : %s\n  核心: %s"
        % (gui_keys, core.DEFAULT_TARGETS))


def test_resolve_targets_all(core):
    assert core.resolve_targets("all") == core.DEFAULT_TARGETS
    assert core.resolve_targets("") == core.DEFAULT_TARGETS
    assert core.resolve_targets("kiro") == ["kiro"]


def test_resolve_targets_alias(core):
    assert core.resolve_targets("claude-code") == ["claude"]
    assert core.resolve_targets("trae-cn") == ["trae"]


def test_kiro_target_shape(core):
    """Kiro 的落点是 steering 目录下的独立文件，不是总规则文件。"""
    t = core.KiroTarget()
    assert t.key == "kiro"
    assert t.home_name == ".kiro"
    assert t.prompt_file.replace("\\", "/") == "steering/pojia-inject.md"
    # steering 下所有 .md 都会被加载，所以必须留镜像层
    assert t.mirror_begin == core.MIRROR_BEGIN

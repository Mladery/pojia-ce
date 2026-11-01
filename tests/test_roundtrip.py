# -*- coding: utf-8 -*-
"""端到端：真实 apply → 二次 apply → 只剩镜像层自愈 → revert。

全程在临时目录里跑，用 ClaudeTarget 当样本（它的落点是单个 Markdown 文件，
最干净）。断言的核心只有一条：**破了甲再还原，必须逐字节回到用户原文**。
"""
import os


def read(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def test_apply_then_revert_is_lossless(core, args, tmp_path):
    home = tmp_path / "claude-home"
    home.mkdir()
    path = home / "CLAUDE.md"
    orig = "# 我自己的全局规则\n\n- 先读代码再改\n- 别乱删文件\n"
    write(str(path), orig)

    t = core.ClaudeTarget()
    args.claude_dir = str(home)

    assert t.apply(args, "apply") == {"fixed": 1}
    txt = read(str(path))
    assert txt.count(t.mark_begin) == 1
    assert txt.count(core.MIRROR_BEGIN) == 1
    assert "我自己的全局规则" in txt, "用户原文被吃掉了"

    # 二次 apply 必须幂等
    t.apply(args, "apply")
    txt2 = read(str(path))
    assert txt2.count(t.mark_begin) == 1, "主块被重复叠加"
    assert txt2.count(core.MIRROR_BEGIN) == 1, "镜像层被重复叠加"
    assert txt2 == txt, "二次 apply 不是幂等的（字节变了）"

    t.revert(args)
    back = read(str(path))
    assert back == orig, "还原没回到原文：\n%r\n!=\n%r" % (back, orig)


def test_apply_heals_mirror_only_file(core, args, tmp_path):
    """主块被客户端吃掉、只剩镜像层时，apply 要能补回双层。"""
    home = tmp_path / "h"
    home.mkdir()
    path = home / "CLAUDE.md"
    t = core.ClaudeTarget()
    args.claude_dir = str(home)

    write(str(path), "用户内容保留\n\n" + t._mirror_block(""))
    t.apply(args, "apply")
    txt = read(str(path))
    assert txt.count(t.mark_begin) == 1
    assert txt.count(core.MIRROR_BEGIN) == 1
    assert "用户内容保留" in txt


def test_revert_on_clean_file_is_noop(core, args, tmp_path):
    """没打过补丁的文件，revert 不该动它。"""
    home = tmp_path / "h2"
    home.mkdir()
    path = home / "CLAUDE.md"
    orig = "纯用户内容\n"
    write(str(path), orig)

    t = core.ClaudeTarget()
    args.claude_dir = str(home)
    t.revert(args)
    assert read(str(path)) == orig


def test_backup_is_pristine_copy(core, args, tmp_path):
    """备份必须是**用户原件**，不能把我们的注入版当原件存下来。"""
    home = tmp_path / "h3"
    home.mkdir()
    path = home / "CLAUDE.md"
    orig = "原始内容\n"
    write(str(path), orig)

    t = core.ClaudeTarget()
    args.claude_dir = str(home)
    t.apply(args, "apply")

    bak = str(path) + t.bak_suffix
    assert os.path.exists(bak), "没留备份"
    assert read(bak) == orig, "备份不是用户原件"

    # 二次 apply 不能覆盖掉原件备份
    t.apply(args, "apply")
    assert read(bak) == orig, "二次 apply 把原件备份覆盖了"


def test_kiro_apply_creates_steering_file(core, args, tmp_path):
    """Kiro 走 steering 目录，且目录不存在时要能自动建。"""
    home = tmp_path / "kiro"
    home.mkdir()
    t = core.KiroTarget()
    args.kiro_dir = str(home)

    t.apply(args, "apply")
    target = home / "steering" / "pojia-inject.md"
    assert target.is_file(), "没在 steering 下建文件"
    txt = read(str(target))
    assert txt.count(t.mark_begin) == 1
    assert txt.count(core.MIRROR_BEGIN) == 1

    t.revert(args)
    assert not target.exists(), "还原后应该把新建的文件删掉"

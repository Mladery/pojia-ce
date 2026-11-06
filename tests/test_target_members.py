# -*- coding: utf-8 -*-
"""每个破甲目标都必须能自己站起来。

上游栽过一次：ZCode 通道的类没继承公共基类，却在写盘那行调用了只有基类才有的
`_mirror_block`。异常发生在备份之后、写入之前 —— 文件没被写坏，`--dry-run` 也
走不到那行，只有真点「破甲」才炸，从 8.27 一路带到 8.32。

两条防线，缺一条都漏：

  · 静态：目标类（连同继承来的方法）引用的每个 `self.x`，都得在本类或基类里有
    定义。基类方法引用子类属性是正常多态，所以检查单位是「具体目标类」而不是
    「每个类」。
  · 运行时：在临时目录里对每个目标真跑一次 apply。静态看不出的是「调用到了但
    传错类型」，只有跑一遍才知道能不能走到底。
"""

import ast

import pytest

from conftest import CORE_PATH


def _assign_targets(node):
    if isinstance(node, ast.Assign):
        return node.targets
    if isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        return [node.target]
    return []


def _own_members(node):
    """类自己声明的成员：方法名、类属性、方法体里 self.x 的赋值。"""
    out = set()
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.add(item.name)
        elif isinstance(item, ast.Assign):
            out.update(t.id for t in item.targets if isinstance(t, ast.Name))
        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            out.add(item.target.id)
    for sub in ast.walk(node):
        for t in _assign_targets(sub):
            if (isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)
                    and t.value.id == "self"):
                out.add(t.attr)
    return out


def _self_loads(fn):
    for sub in ast.walk(fn):
        if (isinstance(sub, ast.Attribute) and isinstance(sub.value, ast.Name)
                and sub.value.id == "self" and isinstance(sub.ctx, ast.Load)):
            yield sub.attr, sub.lineno


def _classes(path):
    tree = ast.parse(open(path, encoding="utf-8").read())
    out = {}

    def walk(node):
        for n in ast.iter_child_nodes(node):
            if isinstance(n, ast.ClassDef):
                out[n.name] = n
            else:
                walk(n)

    walk(tree)
    return out


def _collect(name, nodes, seen=None):
    """类 + 基类链上的成员与全部方法。"""
    seen = seen or set()
    if name in seen or name not in nodes:
        return set(), []
    seen.add(name)
    node = nodes[name]
    members = _own_members(node)
    funcs = [i for i in node.body
             if isinstance(i, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for b in node.bases:
        bname = b.id if isinstance(b, ast.Name) else getattr(b, "attr", "")
        m2, f2 = _collect(bname, nodes, seen)
        members |= m2
        funcs += f2
    return members, funcs


def test_targets_declare_every_member_they_use(core):
    """目标类里不许出现「调用一个自己根本没有的成员」。"""
    nodes = _classes(CORE_PATH)
    problems = []
    for key, cls in core.TARGETS.items():
        members, funcs = _collect(cls.__name__, nodes)
        members |= {"__class__", "__dict__", "__module__", "__doc__"}
        for fn in funcs:
            for attr, line in _self_loads(fn):
                if attr not in members:
                    problems.append("%s(%s).%s -> self.%s 行 %d"
                                    % (cls.__name__, key, fn.name, attr, line))
    assert not problems, "这些成员在类里不存在，运行到就会 AttributeError：\n" + \
        "\n".join(sorted(set(problems)))


SMOKE_SKIP = {"dsh", "wb", "wbintl"}


@pytest.mark.parametrize("key", [k for k in
                                 ("zcode", "codex", "cursor", "claude", "antigravity",
                                  "qwen", "iflow", "trae", "codebuddy", "opencode",
                                  "windsurf", "cline", "copilot", "kiro")])
def test_target_apply_reaches_disk(core, args, tmp_path, key):
    """每个目标在空目录里真跑一次 apply：要么写成功，要么明确跳过，不许抛异常。

    dsh / wb / wbintl 不在其中：它们要扫真实安装、可能动到正在跑的进程，
    不适合在临时目录里跑。那三个由 static 那条兜底。
    """
    if key in SMOKE_SKIP:                      # pragma: no cover
        pytest.skip("需要真实安装")
    cls = core.TARGETS[key]
    home = tmp_path / key
    home.mkdir()
    arg_name = getattr(cls, "arg_name", "")
    if arg_name:
        setattr(args, arg_name, str(home))
    if key == "zcode":
        args.zcode_dir = str(home)

    result = cls().apply(args, "apply")
    assert isinstance(result, dict)
    if key != "codex":                          # codex 预置的不是合法 TOML 才 err
        assert result.get("err") is None, "没写成功也没跳过：%r" % (result,)

# -*- coding: utf-8 -*-
"""仓库自身的一致性检查。

这几条不是功能测试，是「别让仓库说谎」：
  · 源码语法必须过（两个脚本都要能被 ast 解析）
  · README §六 记的哈希必须等于文件真实哈希（改了代码忘更新 = 别人校验不上）
  · 源码与 README 里不许出现上游的版本号（这是硬要求，漏一个就白干）
"""
import ast
import hashlib
import os
import re
import sys

import pytest

from conftest import CORE_PATH, GUI_PATH, README_PATH, ROOT


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@pytest.mark.parametrize("path", [CORE_PATH, GUI_PATH],
                         ids=["破甲一键通.py", "破甲GUI.py"])
def test_sources_parse(path):
    with open(path, encoding="utf-8") as f:
        src = f.read()
    ast.parse(src, filename=path)          # 语法错直接抛


@pytest.mark.parametrize("path", [CORE_PATH, GUI_PATH],
                         ids=["破甲一键通.py", "破甲GUI.py"])
def test_sources_are_lf(path):
    """仓库约定 LF；混进 CRLF 会让 README 里的哈希对不上。"""
    with open(path, "rb") as f:
        blob = f.read()
    assert b"\r\n" not in blob, "文件里混进了 CRLF"


def _readme_hashes():
    """从 README 的校验段里抠出 {文件名: sha256}。"""
    with open(README_PATH, encoding="utf-8") as f:
        text = f.read()
    out = {}
    for m in re.finditer(r"\b([0-9a-f]{64})\b\s+(src/[^\s(]+\.py)", text):
        out[m.group(2)] = m.group(1)
    return out


def test_readme_records_current_hashes():
    recorded = _readme_hashes()
    assert recorded, "README 里找不到校验段"

    for name, expect in recorded.items():
        path = os.path.join(os.path.dirname(os.path.dirname(CORE_PATH)), name)
        assert os.path.isfile(path), "README 记了不存在的文件：%s" % name
        actual = sha256(path)
        assert actual == expect, (
            "README 里 %s 的哈希过期了：\n  README: %s\n  实际  : %s\n"
            "改完代码记得同步 README §六。" % (name, expect, actual))


def test_no_upstream_version_markers():
    """硬要求：仓库里不许出现上游的版本号，否则一眼就能看出改动出处。"""
    pattern = re.compile(r"8\.2[6-9]")
    targets = [CORE_PATH, GUI_PATH, README_PATH]
    hits = []
    for p in targets:
        with open(p, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if pattern.search(line):
                    hits.append("%s:%d: %s" % (os.path.basename(p), i, line.strip()[:80]))
    assert not hits, "出现了上游版本号：\n" + "\n".join(hits)


def test_version_and_edition_are_split(core):
    """VERSION 是机器值（纯数字），EDITION 只拼到显示上。

    把 "-CE" 塞进 VERSION 会让所有已打靶点一夜之间变成「旧版」，全是假警报。
    """
    assert re.fullmatch(r"\d+\.\d+", core.VERSION), "VERSION 必须是纯数字版本号"
    assert core.VER_TAG == core.VERSION + "-" + core.EDITION
    assert core.EDITION and core.EDITION not in core.VERSION


def test_readme_target_count_matches_registry(core):
    """README 写的目标数必须等于注册表里的目标数。"""
    with open(README_PATH, encoding="utf-8") as f:
        text = f.read()
    n = len(core.DEFAULT_TARGETS)
    m = re.search(r"\| 目标数量 \| \d+ \| (\d+) \|", text)
    assert m, "README 差异表里找不到「目标数量」这一行"
    assert int(m.group(1)) == n, "README 说 %s 个目标，注册表里是 %d 个" % (m.group(1), n)


def test_only_stdlib_imports(core):
    """README 承诺「无第三方依赖」—— 顶层 import 必须全在标准库里。

    这条能挡住「顺手 import requests 一下」这种退化：脚本是给人直接
    `python 破甲一键通.py` 跑的，多一个依赖就多一道劝退。
    """
    std = set(getattr(sys, "stdlib_module_names", ()))
    if not std:
        pytest.skip("Python < 3.10 没有 stdlib_module_names，跳过")

    with open(CORE_PATH, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                mods.add(node.module.split(".")[0])

    third = sorted(m for m in mods if m not in std)
    assert not third, "引了第三方库：%s" % third


def test_codesign_anchor_matches_readme():
    """验签锚点证书的 SHA-256 必须和 README 里写的一致。

    这条挡的是「证书轮换了、README 没跟上」—— 用户照着 README 的指纹去比对，
    结果对不上，会以为自己下到了假货。没启用签名（仓库里没有 .cer）时跳过。
    """
    cer = os.path.join(ROOT, "tools", "codesign", "pojia-signing.cer")
    if not os.path.isfile(cer):
        pytest.skip("仓库里没有验签锚点证书，跳过")

    actual = sha256(cer)
    with open(README_PATH, encoding="utf-8") as f:
        text = f.read()
    assert actual in text, (
        "README 里记的锚点证书 SHA-256 与实际不一致：\n  实际: %s\n"
        "换证书后记得同步 README §六。" % actual)


def test_codesign_private_key_never_committed():
    """私钥绝不能出现在工作区里 —— 哪怕被 .gitignore 挡着也不该放在仓库目录。"""
    bad = []
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "build", "dist", "__pycache__")]
        for fn in files:
            if fn.lower().endswith((".pfx", ".pvk", ".p12")):
                bad.append(os.path.join(dirpath, fn))
    assert not bad, "工作区里出现了私钥文件：%s" % bad


LICENSE_SHA = "cf1e09ddd43b7d9927ee4298f4a87b1d6c0a06b33281612e1d86137055fd4d3c"


def test_license_is_upstream_original():
    """LICENSE 必须逐字节保持上游原文。

    这是 MIT 唯一的硬性条件（保留版权声明与许可声明），也是 README §八 对外
    承诺过的事。要改它 —— 比如往后追加我方版权行 —— 先改这里的期望值，并在
    README 里说明理由，别顺手改了就推。
    """
    assert sha256(os.path.join(ROOT, "LICENSE")) == LICENSE_SHA


def test_only_one_mit_license_file():
    """仓库里只许有一份 MIT 正文。

    再放一个 LICENSE-CE / LICENSE-ADDITIONS，GitHub 的许可证识别和各种扫描器
    会判成「双许可 / 冲突」，比不写还含糊。归属与范围写进 NOTICE。
    """
    names = sorted(n for n in os.listdir(ROOT) if n.upper().startswith("LICENSE"))
    assert names == ["LICENSE"], "多出来的许可证文件：%s" % names


def test_notice_covers_both_parties():
    """NOTICE 必须把「上游的」和「本仓库的」都写清楚，缺一边就等于没写。"""
    with open(os.path.join(ROOT, "NOTICE"), encoding="utf-8") as f:
        txt = f.read()
    for needle in ("z91772524-ai", "Mladery", "536ece2", "MIT"):
        assert needle in txt, "NOTICE 里没提 %s" % needle
    assert "不是第二份许可" in txt, "NOTICE 得说清楚它不是第二份许可"


def test_ps1_scripts_have_bom():
    """tools/ 下的 .ps1 必须是 UTF-8 **带 BOM**。

    Windows PowerShell 5.1 遇到不带 BOM 的文件会按 ANSI 读 UTF-8 字节，中文
    注释变成一串乱码，解析器在某个乱码处报「意外的标记」—— 报错行号和真实
    问题差着十万八千里，很难查。这个坑踩过两次，直接上测试。
    """
    tools = os.path.join(ROOT, "tools")
    if not os.path.isdir(tools):
        pytest.skip("没有 tools 目录")

    bad = []
    for fn in sorted(os.listdir(tools)):
        if not fn.lower().endswith(".ps1"):
            continue
        with open(os.path.join(tools, fn), "rb") as f:
            if f.read(3) != b"\xef\xbb\xbf":
                bad.append(fn)
    assert not bad, (
        "这些 .ps1 没有 UTF-8 BOM，5.1 会读成 ANSI 并报一堆假语法错：%s" % bad)

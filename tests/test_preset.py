# -*- coding: utf-8 -*-
"""DSH「破甲模式」预设的落盘/还原测试。

破甲模式是第二种破甲方式：不碰官方文件，只在 profile 的 patch 层插一条
`@deepseek-ai/dsh-agent-preset` 声明，用户从模式下拉里选中才生效。
"""
import os

import pytest


STD_YML = """\
- insert:
    - id: preset-standard
      name: '@deepseek-ai/dsh-agent-preset'
      config:
        id: standard
        order: 1
        plugins:
          - id: persona
            name: '@deepseek-ai/dsh-persona'
            config:
              prefix: You are a coding agent powered by the {{model}} model.
          - id: tool-fs
            name: '@deepseek-ai/dsh-tool-fs'
          - id: tool-pwsh
            name: '@deepseek-ai/dsh-tool-pwsh'
            disabled: !!js process.platform !== 'win32'
"""

PROFILE_YML = """\
- id: ui-chat
  name: "@deepseek-ai/dsh-client-ui-chat"
  config:
    transcriptView: standard
- id: someone-else
  name: "@deepseek-ai/someone-else"
  config:
    enabled: true
"""


@pytest.fixture()
def home(tmp_path):
    """最小 DSH 布局：<home>/profiles/desktop + 一套 @deepseek-ai 安装。"""
    h = tmp_path / "dsh"
    prof = h / "profiles" / "desktop"
    prof.mkdir(parents=True)
    (prof / "cordis.patch.yml").write_text(PROFILE_YML, encoding="utf-8")
    (prof / "package.json").write_text('{"name": "desktop"}\n', encoding="utf-8")

    base = tmp_path / "install" / "node_modules" / "@deepseek-ai"
    std = base / "dsh-web-app" / "presets"
    std.mkdir(parents=True)
    (std / "standard.patch.yml").write_text(STD_YML, encoding="utf-8")
    return h, base


def _yml(home_dir):
    return home_dir / "profiles" / "desktop" / "cordis.patch.yml"


def _persona(core):
    return core.STRONG_INTRO + "\n\n" + core.build_persona_text("", "DSH")


def test_preset_install_writes_marked_row(core, home):
    h, base = home
    ok, note = core.preset_install(str(h), [str(base)], _persona(core))
    assert ok, note
    txt = _yml(h).read_text(encoding="utf-8")
    assert ("# >>> " + core.PRESET_MARK) in txt
    assert ("# <<< " + core.PRESET_MARK) in txt
    assert ("id: " + core.PRESET_ROW) in txt
    # 别人的条目一个都不能动
    assert 'id: ui-chat' in txt and 'id: someone-else' in txt


def test_preset_row_parses_and_sits_second(core, home):
    yaml = pytest.importorskip("yaml")
    h, base = home
    assert core.preset_install(str(h), [str(base)], _persona(core))[0]

    class L(yaml.SafeLoader):
        pass

    L.add_multi_constructor("tag:yaml.org,2002:", lambda l, s, n: None)
    doc = yaml.load(_yml(h).read_text(encoding="utf-8"), Loader=L)
    cfg = doc[-1]["insert"][0]["config"]
    assert cfg["id"] == core.PRESET_ID
    assert cfg["name"] == core.PRESET_NAME
    # 排在 standard(1) 之后、ptc(2) 之前 —— 下拉里是第二项
    assert float(cfg["order"]) == pytest.approx(1.5)
    ids = [p["id"] for p in cfg["plugins"]]
    assert ids[0] == "persona"
    # 工具清单是克隆来的，不是我们自己硬编码的
    assert "tool-fs" in ids and "tool-pwsh" in ids


def test_preset_prefix_carries_persona(core, home):
    yaml = pytest.importorskip("yaml")
    h, base = home
    assert core.preset_install(str(h), [str(base)], _persona(core))[0]

    class L(yaml.SafeLoader):
        pass

    L.add_multi_constructor("tag:yaml.org,2002:", lambda l, s, n: None)
    doc = yaml.load(_yml(h).read_text(encoding="utf-8"), Loader=L)
    pref = doc[-1]["insert"][0]["config"]["plugins"][0]["config"]["prefix"]
    assert core.STRONG_INTRO.split(".")[0] in pref
    assert core.HASH_MARK in pref          # 人格版本哈希，状态检测靠它
    assert core.PASSPHRASE in pref         # 自证口令，这个模式下也得能自证


def test_preset_install_is_idempotent(core, home):
    h, base = home
    assert core.preset_install(str(h), [str(base)], _persona(core))[0]
    first = _yml(h).read_bytes()
    ok, note = core.preset_install(str(h), [str(base)], _persona(core))
    assert ok and "已有" in note
    assert _yml(h).read_bytes() == first


def test_preset_remove_restores_original(core, home):
    h, base = home
    before = _yml(h).read_bytes()
    assert core.preset_install(str(h), [str(base)], _persona(core))[0]
    assert core.preset_remove(str(h))[0]
    assert _yml(h).read_bytes() == before


def test_preset_remove_without_install_is_harmless(core, home):
    h, _base = home
    ok, note = core.preset_remove(str(h))
    assert ok and "无需移除" in note


def test_preset_state_reflects_state(core, home):
    h, base = home
    assert core.preset_state(str(h))[0] == "none"
    assert core.preset_install(str(h), [str(base)], _persona(core))[0]
    assert core.preset_state(str(h))[0] == "ok"
    core.preset_remove(str(h))
    assert core.preset_state(str(h))[0] == "none"


def test_preset_half_installed_is_warn(core, home, tmp_path):
    h, base = home
    assert core.preset_install(str(h), [str(base)], _persona(core))[0]
    # 装完之后 DSH 又开了一个 profile（比如装了 Web 端）—— 那个里面还没有
    web = h / "profiles" / "web"
    web.mkdir(parents=True)
    (web / "cordis.patch.yml").write_text(PROFILE_YML, encoding="utf-8")
    assert core.preset_state(str(h))[0] == "warn"
    # 重跑一次补上，就该恢复 ok
    assert core.preset_install(str(h), [str(base)], _persona(core))[0]
    assert core.preset_state(str(h))[0] == "ok"


def test_preset_absent_profile_is_not_an_error(core, tmp_path):
    ok, note = core.preset_install(str(tmp_path), [], "x")
    assert not ok and "跳过" in note
    assert core.preset_state(str(tmp_path))[0] == "na"


def test_preset_without_standard_fails_softly(core, home, tmp_path):
    h, _base = home
    empty = tmp_path / "empty"
    empty.mkdir()
    ok, note = core.preset_install(str(h), [str(empty)], "x")
    assert not ok and "standard" in note
    # 失败时绝不能留下半个文件
    assert _yml(h).read_text(encoding="utf-8") == PROFILE_YML


def test_preset_dry_run_writes_nothing(core, home):
    h, base = home
    before = _yml(h).read_bytes()
    ok, note = core.preset_install(str(h), [str(base)], _persona(core), dry=True)
    assert ok and "将写入" in note
    assert _yml(h).read_bytes() == before


def test_preset_keeps_foreign_bak_untouched(core, home):
    """备份只在第一次写，重复装不会把备份覆盖成"已装"的样子。"""
    h, base = home
    before = _yml(h).read_bytes()
    core.preset_install(str(h), [str(base)], _persona(core))
    bak = _yml(h).with_suffix(".yml." + core.PRESET_MARK + ".bak")
    assert bak.exists() and bak.read_bytes() == before


# ---- 没解包也要能装：模板从 app.asar 里读 -----------------------------------
import json
import struct


def _make_asar(path, entries):
    """造一个最小可用的 asar：12 字节占位 + json 长度 + header + 数据区。

    entries: {asar 内相对路径: 文件字节}
    """
    files, data = {}, b""
    for rel, blob in entries.items():
        parts = rel.split("/")
        node = files
        for p in parts[:-1]:
            node = node.setdefault(p, {"files": {}})["files"]
        node[parts[-1]] = {"size": len(blob), "offset": str(len(data))}
        data += blob
    hdr = json.dumps({"files": files}).encode("utf-8")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"\0" * 12 + struct.pack("<I", len(hdr)) + hdr + data)


def _std_in_asar(tmp_path):
    root = tmp_path / "asarinst"
    _make_asar(str(root / "resources" / "app.asar"),
               {"dsh/node_modules/@deepseek-ai/dsh-web-app/presets/standard.patch.yml":
                STD_YML.encode("utf-8")})
    return str(root)


def test_asar_read_file(core, tmp_path):
    root = _std_in_asar(tmp_path)
    got = core.asar_read_file(os.path.join(root, "resources", "app.asar"),
                              "dsh/node_modules/@deepseek-ai/dsh-web-app/presets/standard.patch.yml")
    assert got is not None and got.decode("utf-8") == STD_YML
    assert core.asar_read_file(os.path.join(root, "resources", "app.asar"), "nope.yml") is None


def test_preset_std_text_falls_back_to_asar(core, tmp_path):
    root = _std_in_asar(tmp_path)
    txt, src = core.preset_std_text([], [root])
    assert "preset-standard" in txt
    assert src.startswith("app.asar!")


def test_preset_install_without_unpacked_dir(core, home, tmp_path):
    """解包目录不存在（revert 之后就是这样）也要能装 —— 模板走 asar。"""
    h, _base = home
    root = _std_in_asar(tmp_path)
    ok, note = core.preset_install(str(h), [], _persona(core), roots=[root])
    assert ok, note
    assert core.preset_state(str(h))[0] == "ok"
    assert not os.path.isdir(os.path.join(root, "resources", "app")), "不该顺手解包"


def test_preset_reports_clearly_when_nothing_found(core, home, tmp_path):
    h, _base = home
    empty = tmp_path / "void"
    empty.mkdir()
    ok, note = core.preset_install(str(h), [], "x", roots=[str(empty)])
    assert not ok and "standard" in note and "app.asar" in note

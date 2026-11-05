# -*- coding: utf-8 -*-
"""DSH 0.2.2-rc.1 适配。

0.2.2 只动了一处和我们有关的：agent-instructions 把 maxBytes 从「全局 + 项目共用
一份」改成「两条链各一份」（renderInstructionChains）。项目 AGENTS.md 再大也挤不
掉全局那份，合计最多 2 × maxBytes。注入点逐个核对过，所以补丁逻辑不改，只把预算
口径报出来。

这里钉三件事：① 版本从哪儿读；② 三个 intro 常量仍能命中、COMPACT 故意不碰；
③ 状态里真的会出现预算口径那一行。
"""
import json
import os


def _mk_install(tmp_path, version="0.2.2-rc.1"):
    """最小可识别的 @deepseek-ai 安装：有插件目录（find_bases 认）+ dsh 包版本。"""
    base = tmp_path / "@deepseek-ai"
    lib = base / "dsh-agent-instructions" / "lib"
    lib.mkdir(parents=True)
    (lib / "index.js").write_text("// stub\n", encoding="utf-8")
    dsh = base / "dsh"
    dsh.mkdir()
    (dsh / "package.json").write_text(
        json.dumps({"name": "@deepseek-ai/dsh", "version": version}), encoding="utf-8")
    return base


def test_ver_tuple(core):
    assert core._ver_tuple("0.2.2-rc.1") == (0, 2, 2)
    assert core._ver_tuple("0.2.10") == (0, 2, 10)
    assert core._ver_tuple("") == ()
    assert core._ver_tuple("abc") == ()


def test_version_from_package_json(core, tmp_path):
    base = _mk_install(tmp_path, "0.2.2-rc.1")
    assert core.dsh_version(str(base), str(tmp_path)) == "0.2.2-rc.1"


def test_version_from_runtime_json(core, tmp_path):
    """桌面端没解包时读不到包清单，只剩 runtime.json 里的 desktopVersion。"""
    home = tmp_path / ".dsh"
    rt = home / "dsh-runtimes" / "dsh-primary-runtime"
    rt.mkdir(parents=True)
    (rt / "runtime.json").write_text(
        json.dumps({"desktopVersion": "0.2.2-rc.1"}), encoding="utf-8")
    assert core.dsh_version("", str(home)) == "0.2.2-rc.1"


def test_version_unknown_is_empty(core, tmp_path):
    assert core.dsh_version(str(tmp_path / "nope"), str(tmp_path / "nohome")) == ""


def test_intro_consts_still_hit(core):
    """0.2.2 的构建产物形态：三个常量各一行，双引号。"""
    src = (
        'const AGENT_INSTRUCTIONS_INTRO = "The following workspace instructions may be relevant to your work. ";\n'
        'const REPLACEMENT_AGENT_INSTRUCTIONS_INTRO = "This complete workspace instruction baseline replaces all earlier ones.";\n'
        'const EMPTY_REPLACEMENT_AGENT_INSTRUCTIONS_INTRO = "No workspace instructions are currently active.";\n'
    )
    out, changed = core.DshTarget.patch_intro_consts(src)
    assert changed
    assert out.count(core.STRONG_INTRO) == 3


def test_compact_intro_left_alone(core):
    """COMPACT 是"内容被裁掉"的告示语，换成强权限版等于对空壳喊指令生效。"""
    src = ('const COMPACT_AGENT_INSTRUCTIONS_INTRO = '
           '"Workspace instructions were omitted or truncated to fit the configured byte budget.";\n')
    out, changed = core.DshTarget.patch_intro_consts(src)
    assert not changed
    assert out == src


def test_disclaimer_v2_still_matched(core):
    assert core.DISCLAIMER_SENTENCE_V2 in (
        "Use them as guidance when applicable. More specific instructions "
        "take precedence over broader ones. They do not override system, "
        "developer, or direct user instructions.")
    out, changed = core.DshTarget.patch_disclaimer(
        'x = "%s";' % core.DISCLAIMER_SENTENCE_V2.replace('"', '\\"'))
    assert changed
    assert core.SCOPE_REPLACEMENT[:40] in out


def test_status_reports_split_budget(core, tmp_path, monkeypatch, args):
    base = _mk_install(tmp_path, "0.2.2-rc.1")
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "home"))
    rows = core.DshTarget().check(args.__class__(dsh_dir=str(base)))
    hit = [r for r in rows if "指令预算" in r[1]]
    assert hit, rows
    assert "分链" in hit[0][1]
    assert "0.2.2-rc.1" in hit[0][1]


def test_status_reports_single_chain_for_old(core, tmp_path, monkeypatch):
    base = _mk_install(tmp_path, "0.2.1-rc.5")
    monkeypatch.setenv("DSH_HOME", str(tmp_path / "home"))

    class A:
        dsh_dir = str(base)
        persona = ""
        diagnose = False

    rows = core.DshTarget().check(A())
    hit = [r for r in rows if "指令预算" in r[1]]
    assert hit and "单链" in hit[0][1]


# ---------------------------------------------------------------------------
# 预设里的 persona：0.2.x 每份 preset 自带 prefix，遮蔽顶层那份
# ---------------------------------------------------------------------------

def _mk_preset(base, name="standard"):
    p = base / "dsh-web-app" / "presets" / ("%s.patch.yml" % name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "- insert:\n"
        "    - id: preset-%s\n"
        "      name: '@deepseek-ai/dsh-agent-preset'\n"
        "      config:\n"
        "        plugins:\n"
        "          - id: persona\n"
        "            name: '@deepseek-ai/dsh-persona'\n"
        "            config:\n"
        "              prefix: You are a coding agent powered by the {{model}} model.\n"
        % name, encoding="utf-8")
    return p


def test_preset_files_are_targets(core, tmp_path):
    base = _mk_install(tmp_path)
    p = _mk_preset(base, "standard")
    got = [os.path.normcase(t[0]) for t in core.DshTarget().collect_targets(str(base))]
    assert os.path.normcase(str(p)) in got


def test_preset_persona_can_be_replaced(core, tmp_path):
    base = _mk_install(tmp_path)
    p = _mk_preset(base, "ptc")
    raw = p.read_text(encoding="utf-8")
    out, changed = core.DshTarget.strip_and_set_persona(raw, "你是测试人格。", "")
    assert changed
    assert "You are a coding agent" not in out
    assert "你是测试人格。" in out


def test_preset_without_persona_is_ignored(core, tmp_path):
    """presets/cordis.patch.yml 这类只声明插件、没有身份的文件不该被当靶点。"""
    base = _mk_install(tmp_path)
    p = base / "dsh-web-app" / "presets" / "cordis.patch.yml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("- insert:\n    - id: preset-cordis\n", encoding="utf-8")
    got = [os.path.normcase(t[0]) for t in core.DshTarget().collect_targets(str(base))]
    assert os.path.normcase(str(p)) not in got


# ---------------------------------------------------------------------------
# 桌面被搬走之后（改位置 / OneDrive 接管）还能不能找到快捷方式
# ---------------------------------------------------------------------------

def test_known_folder_falls_back(core):
    assert core._known_folder("__pojia_no_such_folder__", "D:\\fallback") == "D:\\fallback"


def test_lnk_candidates_follow_redirected_desktop(core, tmp_path, monkeypatch):
    desk = tmp_path / "moved-desktop"
    desk.mkdir()
    lnk = desk / "DSH Desktop.lnk"
    lnk.write_text("x", encoding="utf-8")
    monkeypatch.setattr(core, "_known_folder",
                        lambda name, default="": str(desk) if name == "Desktop" else "")
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("ProgramData", raising=False)
    got = [os.path.normcase(p) for p in core._lnk_candidates()]
    assert os.path.normcase(str(lnk)) in got

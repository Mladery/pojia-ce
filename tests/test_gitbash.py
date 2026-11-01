# -*- coding: utf-8 -*-
"""Git Bash 接管的落盘 / 还原测试。

背景：DSH 在 Windows 上把 bash 工具和 bash 执行器**一起**关了 ——
dsh-base/cordis.patch.yml 里四处平台开关两两成对，于是模型只剩 pwsh 工具。
这个可选项把四个开关翻过来，并装一个改 PATH 的小插件：因为 Windows 的 PATH 是
「系统在前、用户在后」，C:\\Windows\\System32\\bash.exe（WSL 入口）永远抢先，
改用户 PATH 没用，只能让插件把 Git 的 bin 提到 process.env.PATH 最前。
"""
import os

import pytest

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
          - id: tool-bash
            name: '@deepseek-ai/dsh-tool-bash'
            disabled: !!js process.platform === 'win32'
          - id: tool-pwsh
            name: '@deepseek-ai/dsh-tool-pwsh'
            disabled: !!js process.platform !== 'win32'
"""

EXE = r"C:\Program Files\Git\bin\bash.exe"


@pytest.fixture()
def home(tmp_path, monkeypatch):
    """最小 DSH 布局：<home>/profiles/desktop/cordis.patch.yml。"""
    h = tmp_path / "dsh"
    prof = h / "profiles" / "desktop"
    prof.mkdir(parents=True)
    (prof / "cordis.patch.yml").write_text(PROFILE_YML, encoding="utf-8")
    monkeypatch.setenv("DSH_HOME", str(h))
    return h


def _yml(h):
    return os.path.join(str(h), "profiles", "desktop", "cordis.patch.yml")


def _read(h):
    with open(_yml(h), encoding="utf-8") as f:
        return f.read()


def _entry(block, tool_id):
    """取 plugins 块里某个 `- id: xxx` 条目的所有行。"""
    lines = block.split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "- id: " + tool_id), -1)
    assert start >= 0, "找不到条目 %s" % tool_id
    ind = len(lines[start]) - len(lines[start].lstrip(" "))
    out = [lines[start]]
    for ln in lines[start + 1:]:
        if ln.strip() and (len(ln) - len(ln.lstrip(" "))) <= ind:
            break
        out.append(ln)
    return "\n".join(out)


def test_flip_tool_switches(core):
    """工具开关翻转：bash 打开、pwsh 关掉，其余条目一个字不动。"""
    block = core.preset_plugins_block(STD_YML, None, flip_bash=True)
    assert "disabled: false" in _entry(block, "tool-bash")
    assert "disabled: true" in _entry(block, "tool-pwsh")
    assert "!!js" not in _entry(block, "tool-bash")
    # 不相关的条目原样保留
    assert _entry(block, "tool-fs").strip() == "- id: tool-fs\n            name: '@deepseek-ai/dsh-tool-fs'"


def test_no_flip_keeps_original(core):
    """不开开关时逐字保留 —— 这是"默认什么都不改"的底线。"""
    block = core.preset_plugins_block(STD_YML, None, flip_bash=False)
    assert "!!js process.platform === 'win32'" in block
    assert "!!js process.platform !== 'win32'" in block


def test_flip_adds_disabled_when_missing(core):
    """非 Windows 那份没有 disabled 行 —— 要补上，不能静默漏掉。"""
    std = STD_YML.replace("            disabled: !!js process.platform === 'win32'\n", "")
    block = core.preset_plugins_block(std, None, flip_bash=True)
    assert "disabled: false" in _entry(block, "tool-bash")


def test_patch_text_covers_four_switches(core):
    """四个开关必须成对翻：只开工具不开执行器 = 模型拿到一个跑不了的工具。"""
    t = core.gitbash_patch_text(EXE)
    assert "id: bash-sandbox" in t and "id: pwsh-sandbox" in t
    assert "id: tool-bash" in t and "id: tool-pwsh" in t
    assert t.count("disabled: false") == 2
    assert t.count("disabled: true") == 2
    assert EXE.replace("\\", "\\\\") in t, "路径要按 JSON 转义写进 YAML 双引号标量"


def test_install_writes_and_is_idempotent(core, home):
    ok, note = core.gitbash_install(str(home), EXE)
    assert ok, note
    txt = _read(home)
    assert txt.count("# >>> " + core.GITBASH_MARK) == 1
    assert txt.count("# <<< " + core.GITBASH_MARK) == 1
    assert "someone-else" in txt, "别人的配置不能碰"
    pkg = os.path.join(str(home), "profiles", "desktop", "node_modules", core.GITBASH_ID)
    assert os.path.isfile(os.path.join(pkg, "index.js"))
    assert "process.env.PATH" in open(os.path.join(pkg, "index.js"), encoding="utf-8").read()

    core.gitbash_install(str(home), EXE)               # 再来一遍
    assert _read(home).count("id: " + core.GITBASH_ID) == 1, "重复安装不能叠出第二段"


def test_remove_restores_byte_for_byte(core, home):
    before = _read(home)
    core.gitbash_install(str(home), EXE)
    ok, note = core.gitbash_remove(str(home))
    assert ok, note
    assert _read(home) == before
    pkg = os.path.join(str(home), "profiles", "desktop", "node_modules", core.GITBASH_ID)
    assert not os.path.isdir(pkg)


def test_dry_run_changes_nothing(core, home):
    before = _read(home)
    ok, _note = core.gitbash_install(str(home), EXE, dry=True)
    assert ok
    assert _read(home) == before
    assert not os.path.isdir(os.path.join(str(home), "profiles", "desktop", "node_modules"))


def test_state_flow(core, home):
    st, _note, exe = core.gitbash_state(str(home))
    assert st == "none" and exe == ""
    core.gitbash_install(str(home), EXE)
    st, note, exe = core.gitbash_state(str(home))
    # 这个 exe 在测试机上不一定存在，所以 ok / warn 都算正常，关键是把路径读回来
    assert st in ("ok", "warn")
    assert exe == EXE
    core.gitbash_remove(str(home))
    assert core.gitbash_state(str(home))[0] == "none"


def test_no_profiles_is_harmless(core, tmp_path, monkeypatch):
    """没有 profiles/*（非桌面版布局）时不能炸，也不能乱建目录。"""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("DSH_HOME", str(empty))
    assert core.gitbash_state(str(empty))[0] == "na"
    ok, note = core.gitbash_install(str(empty), EXE)
    assert not ok and "profiles" in note
    assert core.gitbash_remove(str(empty))[0] is False


def test_preset_reinstall_flips_switches(core, home, tmp_path):
    """先按 PowerShell 装好破甲模式，再开 --git-bash：预设里的开关要跟着翻。

    这是个真会踩的顺序问题：`preset_install` 以前见到"已有"就直接跳过，
    于是后开的 Git Bash 只改了 base 那四条，预设子树里还是 win32 的旧值 ——
    结果就是工具与执行器对不上，bash 工具压根不出现。
    """
    base = tmp_path / "install" / "node_modules" / "@deepseek-ai"
    std = base / "dsh-web-app" / "presets"
    std.mkdir(parents=True)
    (std / "standard.patch.yml").write_text(STD_YML, encoding="utf-8")

    core.GITBASH_ON = False
    ok, note = core.preset_install(str(home), [str(base)], "PERSONA", dry=False)
    assert ok, note
    assert "!!js process.platform === 'win32'" in _read(home)

    core.GITBASH_ON = True
    try:
        ok, note = core.preset_install(str(home), [str(base)], "PERSONA", dry=False)
        assert ok, note
        txt = _read(home)
        assert "!!js" not in txt, "预设里的平台条件应当全部被翻转"
        assert "disabled: false" in _entry(txt, "tool-bash")
        assert "disabled: true" in _entry(txt, "tool-pwsh")
        assert txt.count("# >>> " + core.PRESET_MARK) == 1, "重写不能叠出第二段"
        # 幂等：再跑一遍不重写
        before = _read(home)
        core.preset_install(str(home), [str(base)], "PERSONA", dry=False)
        assert _read(home) == before
    finally:
        core.GITBASH_ON = False


def test_standard_override_keeps_identity(core):
    """没装破甲模式时要覆盖官方 standard —— 整条抄，身份字段一个都不能丢。

    cordis 的覆盖是 target[key]=value，给 config 就是整个替换。只写 plugins 会把
    id/name/description/order 抹掉，模式下拉里那一项就废了。
    """
    t = core.standard_preset_override(STD_YML)
    assert t.startswith("# >>> " + core.GITBASH_STD_MARK)
    assert "- id: preset-standard" in t
    assert "id: standard" in t and "order: 1" in t
    assert "name: '@deepseek-ai/dsh-agent-preset'" in t
    assert "!!js" not in t
    assert "disabled: false" in _entry(t, "tool-bash")
    assert "disabled: true" in _entry(t, "tool-pwsh")


def test_install_writes_standard_override_without_preset(core, home, tmp_path):
    """没有破甲模式时，install 要自己补一条 standard 覆盖，否则工具开关改不到。"""
    base = tmp_path / "install" / "node_modules" / "@deepseek-ai"
    std = base / "dsh-web-app" / "presets"
    std.mkdir(parents=True)
    (std / "standard.patch.yml").write_text(STD_YML, encoding="utf-8")

    before = _read(home)
    ok, note = core.gitbash_install(str(home), EXE, bases=[str(base)])
    assert ok, note
    txt = _read(home)
    assert core.GITBASH_STD_MARK in txt
    assert core.gitbash_remove(str(home))[0] is True
    assert _read(home) == before


def test_wsl_bash_is_rejected(core):
    """System32 那个 bash.exe 是 WSL 入口，绝不能当成 Git Bash。"""
    assert core._is_wsl_bash(r"C:\Windows\System32\bash.exe")
    assert core._is_wsl_bash(r"C:\Users\x\AppData\Local\Microsoft\WindowsApps\bash.exe")
    assert not core._is_wsl_bash(r"C:\Program Files\Git\bin\bash.exe")


def test_probe_rejects_missing_file(core):
    assert core.git_bash_probe("") == ("", "")
    assert core.git_bash_probe(os.path.join("Z:", "nope", "bash.exe")) == ("", "")

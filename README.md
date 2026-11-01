# 破甲一键通 · 社区独立版（Community Edition）

> 独立维护的社区版，源自上游最后一版**带源码**的提交（`536ece2`，v8.14）。
> MIT 协议，**非官方**，与原作者无隶属关系；本项目按自己的节奏演进，不跟随上游成品。

---

## 一、这是什么

一个 Python 脚本，把散落的十几套「破甲」工具合并成一份：**一套人格，十六个目标**，可追加、可整块替换、可完整还原。无第三方依赖，Python 3.8+。

本仓库与上游的关系只有一层：`upstream/` 存的是 `536ece2` 那份公开源码的快照，`src/` 是在它基础上摘掉加密封条后的可运行版本。上游 2026-10-13 移除源码、转入 exe + 激活码发行之后，本项目接手独立维护。完整时间线与逐条取证在 [evidence/](evidence/)，正文不再重复。

---

## 二、支持的目标

| 目标 | 说明 |
|---|---|
| `dsh` | DeepSeek Harness（Desktop / npm 全局 / npx 缓存 / 便携版） |
| `wb` | WorkBuddy 国内版（六层靶点 + 账号级云记忆） |
| `wbintl` | WorkBuddy 国际版（`WorkBuddyAI.exe`）—— **本仓库新增** |
| `zcode` | ZCode（`AGENTS.md` / Memory / 技能 / 可选 cjs 系统提示词） |
| `codex` | OpenAI Codex CLI（`config.toml` 的 `model_instructions_file`） |
| `cursor` | Cursor（`.cursor/rules/*.mdc`） |
| `claude` | Claude Code（`CLAUDE.md`） |
| `gemini` | Gemini CLI（`~/.gemini/GEMINI.md`） |
| `qwen` | Qwen Code（`~/.qwen/QWEN.md`） |
| `iflow` | iFlow CLI 心流（`~/.iflow/IFLOW.md`） |
| `trae` | Trae（`~/.trae/rules/project_rules.md`） |
| `codebuddy` | CodeBuddy 腾讯（`~/.codebuddy/CODEBUDDY.md`） |
| `opencode` | OpenCode（`~/.config/opencode/AGENTS.md`） |
| `windsurf` | Windsurf（`~/.codeium/windsurf/memories/global_rules.md`） |
| `cline` | Cline（`~/Documents/Cline/Rules/pojia-inject.md`） |
| `copilot` | GitHub Copilot CLI（`~/.copilot/copilot-instructions.md`） |

---

## 三、快速开始

```bash
python src/破甲一键通.py                     # 交互菜单
python src/破甲一键通.py --status            # 只读：所有目标查一遍
python src/破甲一键通.py --diagnose          # 只读：详细取证
python src/破甲一键通.py --dry-run --apply   # 预演，不改盘
python src/破甲一键通.py --apply --target wb # 真打，只处理 WorkBuddy
python src/破甲一键通.py --revert --target wb
```

所有原始开关（`--apply` / `--revert` / `--persona` / `--guard` / `--snapshot` / `--pick`）都保留。先 `--dry-run`，再动手。

---

## 四、纯净版改了什么

**只删不加。** 移除的 16 个顶层函数全部属于加密封条 / 反篡改链：`_k0` `_k1` `_k2`（密钥派生）、`_d0` `_d1` `_d2` `_st`（解密）、`_seal_decode`、`_seal_read_source`、`_seal_source_problem` `_seal_assert_source` `_seal_verify_source`（源码校验，失败即自毁）、`_seal_alarm`、`_integrity_digest` `verify_integrity`、`_say_agent_reminder`。

`_SEALED` 从「运行时解密」变回一份**明文常量表**，其余逻辑一行没动：备份 / 还原、升级自愈、幂等、护照、上游原有的 15 个目标、全部命令行开关、`--status` 输出格式照旧。

代价说明白：**「改了源码就报警 / 自毁」那层保护没有了**。你拿到的是可随意修改的普通脚本 —— 请自行校验哈希，别用来路不明的副本。机制拆解见 [evidence/反二改保护.md](evidence/反二改保护.md)。

---

## 五、本仓库的改动

### 1. 新增目标 `wbintl`（WorkBuddy 国际版）

上游的 `wb` 定位链够不着国际版：进程正则只认 `\WorkBuddy.exe` 结尾、全盘扫描只扫固定几层、`LOCALAPPDATA\Programs\WorkBuddyAI` 不存在时无兜底。

`wbintl` 复用同一套靶点 / 补丁 / 备份逻辑，只改定位：**进程反查优先**（按 `WorkBuddyAI.exe` 命令行反查安装根，比扫盘准）→ 切换工具配置 → `LOCALAPPDATA` → 快捷方式 → 目录遍历 → 注册表；安装根判据加验 `WorkBuddyAI.exe` 在场（两版模板同构，单查模板会把国内版目录误收）；数据目录指向 `~/.workbuddy-ai`；备份后缀 `.unlockbak-ai`，与国内版的 `.unlockbak` 互不误认。

别名 `wbai` / `workbuddy-ai` / `workbuddy-intl`，手动指定用 `--wbintl-install` / `--wbintl-data`。

### 2. 安装根发现增强

原来的定位链只认 `Program Files`、`LOCALAPPDATA\Programs` 和盘符根下几个固定目录名。实际装机大量是「自定义盘符 + 自定义一级目录」—— `J:\Workbuddy-GLOBAL\WorkBuddyAI`、`H:\Workbuddy`、`J:\wb\WorkBuddyManager` 都属于这一类，固定候选一个都命中不了。新增三条线索：

| 来源 | 做法 | 本机实测 |
|---|---|---|
| 切换工具配置 | 在 `~/.wb-switch`、`~/.cc-switch` 的 JSON 里反查 exe 绝对路径 | 0.06 s |
| 开始菜单 / 桌面快捷方式 | 纯标准库解析 `.lnk` 目标 | 0.04 s |
| 有界目录遍历 | 按「深度优先于盘符」找 exe，8 s / 4 万条双预算 | 0.03–4.9 s |

两个配套细节：

- **互斥判据**：两版目录里都有同一份 `workbuddy-prompt.tpl`，只查模板会把国际版认成国内版。国内版新增「`WorkBuddyAI.exe` 不在场」这一条，自动发现层统一使用它。
- **来源标注**：`--status` 会显示 `← 切换工具配置` / `← 快捷方式` / `← 进程反查`，定位错了能立刻看出是哪一层判断的。

`.lnk` 解析是自己按 Shell Link 格式读的，不走 `WScript.Shell` —— COM 实例化在受管环境里会被安全策略直接拦掉（本机实测如此），而且每次定位都起一个 COM 对象也不值得。

---

## 六、校验

```
c4f35965114607d87c85550bd203d996593125261dba2a7d2c34107a621ad2fb  src/破甲一键通.py           (341,215 B / LF)
f470a41ac51116fd12052f8c01eecf2d08c87c26100d3c26472134b7b22a73d0  upstream/破甲一键通.v8.14.py (351,393 B / LF)
```

`src/` 随本仓库每次改动而变，上面的值对应本版；`upstream/` 是不动的锚点，可直接对着上游复核：

```bash
git clone https://github.com/z91772524-ai/pojia-next && cd pojia-next
git show 536ece2:破甲一键通.py | sha256sum
```

---

## 七、仓库内容

```
LICENSE                        上游 MIT 原文，未改动（Copyright (c) 2026 z91772524-ai）
src/破甲一键通.py               纯净版核心：摘掉 16 个加密封条函数，可直接跑
upstream/破甲一键通.v8.14.py    上游 536ece2 的原始核心，未改动，用于比对
evidence/                      取证材料：提交时间线、群聊记录、防二改机制拆解
```

不带的：`破甲GUI.py`。上游 GUI 绑了群号登录、激活码校验、`cloud.json` 存档、云控下发与静默更新，属成品发行侧的东西，与本仓库定位冲突。需要图形界面就用官方成品。

---

## 八、许可、独立性与免责

- 全部代码来自上游 `z91772524-ai/pojia-next`，版权归原作者，按 **MIT License** 使用与再分发。`LICENSE` 保留上游原文未改 —— 这是 MIT 唯一的硬性条件。本仓库自身的改动同样以 MIT 发布，不主张对原作的额外权利。
- **独立维护，不是上游的分支跟踪者。** 代码来源仅两份：`536ece2` 的快照与在此之上摘除封条的净化版。上游此后的一切成品（exe / 激活码 / 云控）与本仓库无任何代码或分发关系；本项目不追其版本号，不合并其后续提交。
- 鸣谢 `z91772524-ai` 及全部上游贡献者 —— 没有那份公开源码就没有这个仓库。鸣谢是 MIT 授权事实下的礼节，不构成对上游后续任何做法的认可。
- 与 `z91772524-ai` 无隶属关系，不代表其立场，不分发其成品 exe，不代办激活码。代码按「现状」提供，无任何担保；用途自负，请遵守所在地法律法规与目标软件的服务条款。

> 仓库当前在 GitHub 上暂以 fork 形式存在（保留 `forked from` 页签以便溯源）；detach 后本 README 无需改动。

---

## 九、证据材料

`evidence/` 里是三份独立文档，与工具本身无关，供需要溯源的人自取：

- [EVIDENCE.md](evidence/EVIDENCE.md) —— 上游 112 条提交逐条记录与关键节点
- [群聊取证.md](evidence/群聊取证.md) —— 官方群推广行为的逐条取证（QQ 号已打码）
- [反二改保护.md](evidence/反二改保护.md) —— 三层「防二改」机制拆解：技术有效，许可无效

# 破甲一键通 · 社区版（Community Edition）

[![CI](https://github.com/Mladery/pojia-ce/actions/workflows/ci.yml/badge.svg)](https://github.com/Mladery/pojia-ce/actions/workflows/ci.yml)
[![Build](https://github.com/Mladery/pojia-ce/actions/workflows/build.yml/badge.svg)](https://github.com/Mladery/pojia-ce/actions/workflows/build.yml)

> 仓库 `Mladery/pojia-ce`，对外版本号 **`v8.52-CE`**。
> 独立维护的社区版，源自上游最后一版**带源码**的提交（`536ece2`，v8.14）。
> MIT 协议，**非官方**，与原作者无隶属关系；本项目按自己的节奏演进，不跟随上游成品。

仓库名刻意不叫 `pojia-next`：那和上游同名，容易被当成「上游的正统续作」。这里只是社区自己维护的一份分支，`-ce` 就是 Community Edition，不主张任何继承关系。

改动逐版记录在 **[CHANGELOG.md](CHANGELOG.md)**；本文件只讲怎么用。

---

## 一、这是什么

一个 Python 脚本，把散落的十几套「破甲」工具合并成一份：**一套人格，十七个目标**，可追加、可整块替换、可完整还原。无第三方依赖，Python 3.8+。

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
| `trae` | Trae（国内版 `~/.trae`、国际版 `~/.trae-cn`，均读 `rules/project_rules.md`） |
| `codebuddy` | CodeBuddy 腾讯（`~/.codebuddy/CODEBUDDY.md`） |
| `opencode` | OpenCode（`~/.config/opencode/AGENTS.md`） |
| `windsurf` | Windsurf（`~/.codeium/windsurf/memories/global_rules.md`） |
| `cline` | Cline（`~/Documents/Cline/Rules/pojia-inject.md`） |
| `copilot` | GitHub Copilot CLI（`~/.copilot/copilot-instructions.md`） |
| `kiro` | Kiro（`~/.kiro/steering/pojia-inject.md`，steering 全量加载）—— **本仓库新增** |

---

## 三、快速开始

```bash
python src/破甲一键通.py                     # 交互菜单
python src/破甲GUI.py                        # 图形界面（本机网页，自动开浏览器）
python src/破甲一键通.py --status            # 只读：所有目标查一遍
python src/破甲一键通.py --check             # 只读体检：含会话快照的密钥体检
python src/破甲一键通.py --diagnose          # 只读：详细取证
python src/破甲一键通.py --dry-run --apply   # 预演，不改盘
python src/破甲一键通.py --apply --target wb # 真打，只处理 WorkBuddy
python src/破甲一键通.py --apply --target dsh --dsh-mode preset   # DSH 破甲模式：不改官方文件
python src/破甲一键通.py --apply --target dsh --git-bash          # Windows：默认命令工具换成 Git Bash（默认关）
python src/破甲一键通.py --clean-spill --target wb   # 清过期的会话快照
python src/破甲一键通.py --revert --target wb
pojia-ce.exe                                 # 打包版：双击/直接跑就开图形界面
pojia-ce.exe --menu                          # 打包版：走命令行交互菜单
```

所有原始开关（`--apply` / `--revert` / `--persona` / `--guard` / `--snapshot` / `--pick`）都保留。先 `--dry-run`，再动手。

### 免安装：直接下可执行文件

不想装 Python 就用打包版 —— CI 每次推 `main` 都会打一遍，打 tag 时自动发 Release：

| 平台 | 文件 |
|---|---|
| Windows x64 | `pojia-ce-windows-x64.exe` |
| Linux x64 | `pojia-ce-linux-x64` |
| macOS Intel | `pojia-ce-macos-x64` |
| macOS Apple Silicon | `pojia-ce-macos-arm64` |

在 [Actions](https://github.com/Mladery/pojia-ce/actions/workflows/build.yml) 里点最新一次运行，页面底部 Artifacts 就能下；打了 tag 的版本在 [Releases](https://github.com/Mladery/pojia-ce/releases) 里。

用法和脚本一模一样，把 `python 破甲一键通.py` 换成可执行文件即可。行为也一致：

- `persona.md` 放在可执行文件**旁边**就会被读到；
- `状态/`（手动记住的目录）和 `破甲日志.txt` 也落在它旁边，不会写进临时目录；
- Windows 的守护任务会直接指向这个 exe，不再拼 `pythonw.exe`。

三点要提前说：

- **macOS 首次运行会被 Gatekeeper 拦**（未签名）。解掉隔离标记即可：`xattr -d com.apple.quarantine ./pojia-ce-macos-arm64`。
- **Windows Defender 可能对单文件 exe 报毒** —— PyInstaller 的引导器是常见误报对象。签名（见 [CHANGELOG 的 v8.5-CE](CHANGELOG.md#v85-ce-2026-11-01)）能让属性页显示发布者、本机少挨一次拦截，但**改变不了别人机器上的判断**。要绝对干净就用源码跑，或者自己 `python -m PyInstaller` 打一份。
- **打包版双击就进图形界面**：不带参数直接跑（或双击）会开浏览器页面，不用记命令；想看命令行菜单加 `--menu`。界面是打进包里的数据文件，由核心用 runpy 在**进程内**拉起（包里没有解释器可拉第二个进程）；页面里每个动作把 exe 自己当子进程跑，输出照样实时流回页面。不想让它自动开浏览器就设 `POJIA_GUI_NO_OPEN=1`。
- 带任何参数时不会抢：`--status` / `--apply` / 守护任务用的 `--quiet` 都照旧走命令行。

---

## 四、纯净版改了什么

**只删不加。** 移除的 16 个顶层函数全部属于加密封条 / 反篡改链：`_k0` `_k1` `_k2`（密钥派生）、`_d0` `_d1` `_d2` `_st`（解密）、`_seal_decode`、`_seal_read_source`、`_seal_source_problem` `_seal_assert_source` `_seal_verify_source`（源码校验，失败即自毁）、`_seal_alarm`、`_integrity_digest` `verify_integrity`、`_say_agent_reminder`。

`_SEALED` 从「运行时解密」变回一份**明文常量表**，其余逻辑一行没动：备份 / 还原、升级自愈、幂等、护照、上游原有的 15 个目标、全部命令行开关、`--status` 输出格式照旧。

代价说明白：**「改了源码就报警 / 自毁」那层保护没有了**。你拿到的是可随意修改的普通脚本 —— 请自行校验哈希，别用来路不明的副本。机制拆解见 [evidence/反二改保护.md](evidence/反二改保护.md)。

---

## 五、本仓库的改动

上游自 v8.14 起不再公开源码，本项目接手独立维护，改动按版本走。**逐条实现细节、踩过的坑、验证方式都在 [CHANGELOG.md](CHANGELOG.md)**，这里只留索引和最值得单独说的几件。

| 版本 | 主题 |
|---|---|
| [`v8.52-CE`](CHANGELOG.md#v852-ce-2026-11-01) | 打包版带 GUI / Cython 预编译 / 构建收进 `tools/` / 许可归属 |
| [`v8.51-CE`](CHANGELOG.md#v851-ce-2026-11-01) | Git Bash 接管 / DSH 破甲模式 / 运行时守卫 / 还原彻底化 |
| [`v8.5-CE`](CHANGELOG.md#v85-ce-2026-11-01) | 自动化测试与 CI / 四平台可执行文件 / Windows 代码签名 |
| [`v8.4-CE`](CHANGELOG.md#v84-ce-2026-11-01) | `kiro` 目标 / 补齐十个 `--<key>-dir` 参数 |
| [`v8.3-CE`](CHANGELOG.md#v83-ce-2026-11-01) | 写后自检 / 长路径 / 镜像层 / Electron 保险丝 / Trae 双发行版 |
| [`v8.2-CE`](CHANGELOG.md#v82-ce-2026-11-01) | `wbintl` 目标 / 四源安装根发现 / 快照体检 / 图形界面 / DSH 0.2.1-rc.5 适配 |

### 六件最值得单独说的

**1. `wbintl` 与四源安装根发现。** 上游的 `wb` 够不着国际版（`WorkBuddyAI.exe`），`wbintl` 复用同一套靶点与备份逻辑，只换定位链。定位链本身也重写了：进程反查 → 切换工具配置 → 开始菜单 / 桌面快捷方式（纯标准库解析 `.lnk`）→ 有界目录遍历，按「准、快、省」排序，带来源标注（`← 快捷方式`），定位错了能一眼看出是哪层判断的。DSH 和 ZCode 共用同一套。

**2. 会话快照体检。** WorkBuddy 每次启动都在 `%TEMP%` 留一份产品配置副本（带明文 `apiKey`），崩溃或强杀就留在那儿。`--apply` / `--check` 会报数量、体积、过期份数，并做一次**只输出脱敏形态**的密钥体检；默认只报不删，要清得明说 `--clean-spill` / `--purge-spill`。

**3. 镜像层（第二重申）。** 长会话里开头的人格声明会被挤出热区，所以在主块之后不远处再放一小块——只含覆盖声明与自证口令，独立标记，任一块单独在位都能工作。还原时两块都剥干净，逐字节回原样。

**4. DSH 破甲模式（社区特供）。** 除了改磁盘文件的注入模式，还能只在 profile 的 patch 层注册一条预设：**一个官方文件都不改**，模式下拉里多一项「破甲模式」，选中才生效。工具清单从本机已装的 standard 预设文本级克隆，宿主升级也跟得上。另配一个运行时守卫 `pojia-ce-guard`：一轮正常收尾却是拒答话术、或异常收尾，就补一句「继续」；用户自己按了停止、或刚发过话，不动。

**5. 还原的彻底性。** 「补丁还原了」不等于「回到原样」：解包目录、自建备份、熔丝、中间产物、专属目录都一并清，还原后留「还原戳」防止 `--status` 又把它解包回来。旁路 `.bak` 被清理软件删掉时，从 `managed-prompts/pojia-yijiantong/pristine/` 的**原档保险库**取原档，不再只能报 `nobak`。

**6. Git Bash 接管（Windows，可选，默认关）。** 官方在 Windows 上把 bash 工具和执行器一起关了，只剩 PowerShell 5.1 —— 反引号转义、`$` 展开、没有 `&&`、here-string 必须顶格，模型天天在这上面翻车。`--git-bash` 把四个平台开关翻过来，并装一个十几行的插件把 Git 的 `bin` 提到 `PATH` 最前（Windows 的 `System32\bash.exe` 是 WSL 入口，永远抢先）；本机没有 Git Bash 就从 npmmirror / 清华 / GitHub 下 PortableGit，解压即用、不写注册表。WSL 的 bash 会被真跑一次 `uname -s` 判死并剔除。默认关，因为它改的是宿主行为。

### 与上游的差异

截至 2026-11-01，与上游最新公开文档逐条比对：

| 能力 | 上游 | 本仓库 |
|---|---|---|
| WorkBuddy 国际版 | 只有 `wb` 一个目标，未区分国内版 / 国际版 | `wbintl` 独立目标 |
| 开始菜单 / 桌面快捷方式解析 | 未见 | 纯标准库 `.lnk` 解析 |
| 切换工具配置反查（wb-switch / cc-switch） | 未见 | 有 |
| 会话快照的密钥体检 | 未见 | 有（只报脱敏形态） |
| 安装目录发现 | Program Files / `LOCALAPPDATA` / 注册表 / 所有盘符 / 运行中进程 / npm | 同左，另加进程反查 / 切换工具配置 / 快捷方式 / 有界遍历四条；且 DSH / ZCode 共用同一套发现 |
| DSH `app.asar` 内插件 | 未见（只处理磁盘上散开的文件） | 解包到 `resources/app/` 再补，带完整性硬校验 |
| DSH 0.2.1-rc.5 常量改名 | 未见 | 新旧五个 intro 常量名全认 |
| Windows 默认命令工具 | 只有 PowerShell（bash 工具被平台条件禁用） | 可选 Git Bash 接管：自动找/下 Git Bash，工具与执行器一起切 |
| 长上下文重复注入 | 未见 | 主块 + 独立镜像块，任一在位即可 |
| Electron `OnlyLoadAppFromAsar` 保险丝 | 未见 | 自动探测并关闭，改前留备份 |
| Trae 国内版 / 国际版 | 只认一个配置目录 | `~/.trae` / `~/.trae-cn` 双候选 |
| Kiro（steering） | 未见 | 独立目标，写 `~/.kiro/steering/pojia-inject.md` |
| `--<key>-dir` 手动指定 | 未见 | 按目标表兜底注册，加目标自动就有 |
| 写后自检 | 未见 | 回读复核，不合格即按备份回滚 |
| Windows 长路径 | 未见 | 超过 240 字符自动加 `\\?\` 前缀 |
| 免安装可执行文件 | 只有 Windows exe（且带封条/激活码） | Windows / Linux / macOS 四平台，CI 自动出 |
| 打包版的行为一致性 | — | 人格文件、状态目录、日志都跟着可执行文件走 |
| 目标数量 | 15 | 17 |

> 保留意见：上游自 v8.14 起不再公开源码，上表依据其 README 与更新日志比对，「未见」只代表文档未声明，不等于其代码中一定没有。安装目录发现一项上游明确是有的，差异在「猜固定目录名」与「按盘符 × 深度实找」之间。

---

## 六、校验

```
be056752f8d5a0cdb437522e17f27fc3515e2852d54a78d421111e7080e9174c  src/破甲一键通.py           (477,621 B / LF)
e380390e03a0eee1b4a68e8f9bbee055c613ff01b14b153b0fe4d59a974040be  src/破甲GUI.py              (26,642 B / LF)
f470a41ac51116fd12052f8c01eecf2d08c87c26100d3c26472134b7b22a73d0  upstream/破甲一键通.v8.14.py (351,393 B / LF)
```

`src/` 下的两份随本仓库每次改动而变，上面的值对应本版；`upstream/` 是不动的锚点，可直接对着上游复核：

```bash
git clone https://github.com/z91772524-ai/pojia-next && cd pojia-next
git show 536ece2:破甲一键通.py | sha256sum
```

`src/破甲一键通.py` 现在比 `upstream/` 大 126,228 B —— §四 的「只删不加」说的是摘封条那一步（净减）；多出来的字节来自 v8.2 之后的新增功能（`wbintl`、`.lnk` 解析、快照体检、DSH 0.2.1-rc.5 适配、镜像层、保险丝探测、写后自检、Kiro 目标、破甲模式、守卫、Git Bash 接管、打包适配），逐条见 [CHANGELOG](CHANGELOG.md)。

版本号分两段存：`VERSION = "8.52"` 是写进护照和标记块的**机器值**，`EDITION = "CE"` 只拼到对外显示上（`VER_TAG = "8.52-CE"`）。把 `-CE` 塞进护照会让所有已打的靶点一夜之间变成「旧版」，全是假警报。

### 产物校验（两条独立通道）

源码用上面的哈希校验。**下载的可执行文件用另一套**，因为哈希和文件在同一处发布 —— 能改仓库的人可以同时改掉两者，那不叫交叉验证。

**通道一：签名 + 仓库钉定的公钥证书（Windows）。** 私钥只在发布者手里，伪造不出签名。锚点证书就放在仓库里：

```
tools/codesign/pojia-signing.cer
  主题     : CN=Mladery, O=Mladery CE, C=CN
  SHA-256  : ee95267b61a4965829338d80a792d3b3810d6b0c2d8045d6842ce1fb22c8e413
  有效期至 : 2036-11-01（RSA 4096 / SHA-256）
```

```powershell
.\tools\verify-windows.ps1 -Exe pojia-ce-windows-x64.exe
# [ OK ] 签名者与锚点证书一致 → 退出码 0
# [FAIL] 签名者不是仓库里钉的那张证书 → 退出码 1
```

脚本比对的是**整张证书的 SHA-256**，不是主题名 —— 主题名谁都能写，指纹不能。自己手动看也行：文件属性 → 数字签名 → 详细信息，签名者应是 `Mladery`；或者 `Get-AuthenticodeSignature` 看 `SignerCertificate` 的指纹。

链状态显示 `UnknownError` 是正常的：自签根没装进你的信任存储。这不影响「签名有效且来自这张证书」这个结论 —— 想让状态变成 `Valid`，把 `tools/codesign/pojia-signing.cer` 导入「受信任的根证书颁发机构」。

**通道二：SHA256SUMS.txt（全平台）。** 每次构建由 `checksums` job 汇总四个产物生成，打 tag 时随 Release 一起发：

```bash
sha256sum -c SHA256SUMS.txt        # Linux
shasum -a 256 -c SHA256SUMS.txt    # macOS
```

Linux / macOS 的产物没有签名（`codesign` / `gpg` 那套要另外的证书和流程），所以对它们来说这份校验和就是唯一的完整性凭据。

---

## 七、仓库内容

```
LICENSE                        MIT 正文（未改）+ 两行版权：上游 z91772524-ai、本仓库 Mladery
NOTICE                         归属说明：哪部分是上游的、哪部分是本仓库的
README.md                      本文件：工具说明与索引
CHANGELOG.md                   更新日志：逐版改动、实现细节、踩过的坑
src/破甲一键通.py               纯净版核心：摘掉 16 个加密封条函数，可直接跑
src/破甲GUI.py                  图形界面：本机网页 UI，零依赖
upstream/破甲一键通.v8.14.py    上游 536ece2 的原始核心，未改动，用于比对
tests/                         测试：标记块往返 / 保险丝 / 目标注册表 / 命令行冒烟 / Git Bash
docs/release-notes/            每个 tag 的发布说明
.github/workflows/ci.yml       CI：三平台 × 多 Python 版本跑一遍
.github/workflows/build.yml    Build：四个平台打单文件可执行文件，打 tag 发 Release
tools/                         签名工具：生成证书 / 签名 / 验签 / 发布 secret
tools/codesign/                验签锚点：公钥证书（只有公钥，可以公开）
evidence/                      取证材料：提交时间线、群聊记录、防二改机制拆解
```

跑测试只需要 pytest（脚本本身零依赖）：

```bash
python -m pip install pytest
python -m pytest tests -q
```

测试全部在临时目录里操作，**不碰真实的 `~`**，也不要求装了任何客户端 —— 干净机器上照样能跑完。

**注意同名**：上游发行包里的 `破甲GUI.py` 和本仓库的 `src/破甲GUI.py` **只是重名，不是同一份代码**，两者没有任何继承关系。

- 上游那份绑了群号登录、激活码校验、`cloud.json` 存档、云控下发与静默更新，属成品发行侧的东西 —— 本仓库不收、不改、不兼容，也别指望拿它替换 `src/破甲GUI.py`。
- 本仓库这份是重新写的本机网页 UI：没有账号、没有激活码、不联网、不自动更新，只调本地核心脚本。要图形界面用这个就够，不必去装官方成品。

---

## 八、许可、独立性与免责

- **代码分两部分，授权一致，边界写在 [NOTICE](NOTICE) 里。** `upstream/` 的快照与 `src/` 里摘掉封条后保留下来的那部分来自上游 `z91772524-ai/pojia-next`（提交 `536ece2`），版权归原作者；**本仓库新增与重写的部分**（`wbintl` / `kiro` 目标、四源定位链、镜像层、DSH 破甲模式与运行时守卫、Git Bash 接管、`--gui` 网页界面、测试、打包与签名工具）版权归 **Mladery**（本仓库维护者）。两部分同以 **MIT** 发布，`LICENSE` 里两行版权并列：

  ```
  Copyright (c) 2026 z91772524-ai
  Copyright (c) 2026 Mladery
  ```

  许可正文（`Permission is hereby granted` 到文件末尾）一字未改 —— MIT 要求的是「保留版权声明与许可声明」，往上追加一行自己的版权不违反这条。测试盯着两点：两行版权都在、正文的 sha256 不变。
  - 只放**一份** MIT 正文（`LICENSE`），不另起第二份：多一个 LICENSE 文件会让 GitHub 的许可证识别和各种扫描器判成「双许可 / 冲突」，比不写还含糊。归属与范围单独写进 [NOTICE](NOTICE)。
- **独立维护，不是上游的分支跟踪者。** 起点只有 `536ece2` 那份快照；此后 `src/` 的每一次改动都是本项目自己写的（逐版记录见 [CHANGELOG](CHANGELOG.md)）。上游此后的一切成品（exe / 激活码 / 云控）与本仓库无任何代码或分发关系；本项目不追其版本号，不合并其后续提交。
- **名字上也不攀附。** 仓库原名 `pojia-next` 与上游同名，容易被读成「上游的正统续作」，现已改为 `pojia-ce`；版本号带 `-CE` 后缀，一眼看出是社区分支而不是官方版本。工具本身仍叫「破甲一键通」—— 那是对上游那个工具的描述性称呼，改名会让老用户找不到东西。
- 鸣谢 `z91772524-ai` 及全部上游贡献者 —— 没有那份公开源码就没有这个仓库。鸣谢是 MIT 授权事实下的礼节，不构成对上游后续任何做法的认可。
- 与 `z91772524-ai` 无隶属关系，不代表其立场，不分发其成品 exe，不代办激活码。代码按「现状」提供，无任何担保；用途自负，请遵守所在地法律法规与目标软件的服务条款。

> 仓库当前在 GitHub 上暂以 fork 形式存在（保留 `forked from` 页签以便溯源）；detach 后本 README 无需改动。

---

## 九、证据材料

`evidence/` 里是三份独立文档，与工具本身无关，供需要溯源的人自取：

- [EVIDENCE.md](evidence/EVIDENCE.md) —— 上游 112 条提交逐条记录与关键节点
- [群聊取证.md](evidence/群聊取证.md) —— 官方群推广行为的逐条取证（QQ 号已打码）
- [反二改保护.md](evidence/反二改保护.md) —— 三层「防二改」机制拆解：技术有效，许可无效

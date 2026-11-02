# 破甲一键通 · 社区版（Community Edition）

[![CI](https://github.com/Mladery/pojia-ce/actions/workflows/ci.yml/badge.svg)](https://github.com/Mladery/pojia-ce/actions/workflows/ci.yml)
[![Build](https://github.com/Mladery/pojia-ce/actions/workflows/build.yml/badge.svg)](https://github.com/Mladery/pojia-ce/actions/workflows/build.yml)

> 仓库 `Mladery/pojia-ce`，对外版本号 **`v8.54-CE`**。
> 独立维护的社区版，源自上游最后一版**带源码**的提交（`536ece2`，v8.14）。
> MIT 协议，**非官方**，与原作者无隶属关系；本项目按自己的节奏演进，不跟随上游成品。
> 仅限在**自己有权管理的本机设备**上使用。**下载或运行前，请先读「[九、法律免责与合规使用声明](#九法律免责与合规使用声明)」。**

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
python src/破甲一键通.py --mac-check         # macOS：查 .app 签名还完整吗（只读）
python src/破甲一键通.py --mac-check --resign # macOS：把签名失效的包 ad-hoc 重签
pojia-ce.exe                                 # 打包版：双击/直接跑就开图形界面
pojia-ce.exe --menu                          # 打包版：走命令行交互菜单
```

所有原始开关（`--apply` / `--revert` / `--persona` / `--guard` / `--snapshot` / `--pick`）都保留。先 `--dry-run`，再动手。

### macOS 用户先看这一段

macOS 上的客户端都是 `.app` 包，而 `.app` 是**整体签名**的 —— 破甲往里写文件（asar 解包目录、`managed-prompts/`、`.bak` 备份）会让签名失效。带隔离标记的包（刚下载、一次都没启动过）再启动时 Gatekeeper 会报「已损坏，无法打开」；已经启动过一次的通常没事。

所以 v8.54 起，**改完包内文件会自动 ad-hoc 重签**（`codesign --force --deep --sign -`，只在真动过 `.app` 时才跑）。重签后厂商签名变成自签名，首次打开要右键 → 打开。

已经卡住打不开的，跑：

```bash
pojia-ce --mac-check            # 看哪些包的签名坏了（只读）
pojia-ce --mac-check --resign   # 顺手签回去
```

两条手动救援命令，macOS 自带：

```bash
codesign --force --deep --sign - /Applications/Xxx.app
xattr -cr /Applications/Xxx.app
```

还有两点 macOS 专属：客户端要**连托盘一起退干净**再重开（`Cmd+Q` 不够），以及 `/Applications` 里的包要求属主是你自己 —— 装到别处或 `~/Applications` 更省事。

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
| [`v8.54-CE`](CHANGELOG.md#v854-ce-2026-11-02) | macOS：改完 .app 自动 ad-hoc 重签 / `--mac-check` 体检 |
| [`v8.53-CE`](CHANGELOG.md#v853-ce-2026-11-01) | 界面重做（面向普通用户） / DSH 破甲方式可选 / Git Bash 开关进界面 |
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
5c3eac449bcbff8be9c9236e6c4a05fb37526d07a1f6aec96acc7fa2baa94be4  src/破甲一键通.py           (488,823 B / LF)
4ff11a57d9d349d47b78e3237b276fa0b763bbd1ad547d15f119892e906fe62c  src/破甲GUI.py              (46,610 B / LF)
f470a41ac51116fd12052f8c01eecf2d08c87c26100d3c26472134b7b22a73d0  upstream/破甲一键通.v8.14.py (351,393 B / LF)
```

`src/` 下的两份随本仓库每次改动而变，上面的值对应本版；`upstream/` 是不动的锚点，可直接对着上游复核：

```bash
git clone https://github.com/z91772524-ai/pojia-next && cd pojia-next
git show 536ece2:破甲一键通.py | sha256sum
```

`src/破甲一键通.py` 现在比 `upstream/` 大 137,430 B —— §四 的「只删不加」说的是摘封条那一步（净减）；多出来的字节来自 v8.2 之后的新增功能（`wbintl`、`.lnk` 解析、快照体检、DSH 0.2.1-rc.5 适配、镜像层、保险丝探测、写后自检、Kiro 目标、破甲模式、守卫、Git Bash 接管、打包适配、macOS 签名重签），逐条见 [CHANGELOG](CHANGELOG.md)。

版本号分两段存：`VERSION = "8.54"` 是写进护照和标记块的**机器值**，`EDITION = "CE"` 只拼到对外显示上（`VER_TAG = "8.54-CE"`）。把 `-CE` 塞进护照会让所有已打的靶点一夜之间变成「旧版」，全是假警报。

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

> 本仓库已于 2026-11-02 脱离上游 fork 网络（`fork = false`，无 `parent` / `source`），成为独立仓库；55 条历史、5 个 tag 与 5 个 Release 原样保留。

---

## 九、法律免责与合规使用声明

> **请先读这一节再下载。** 本项目是**修改本机提示词模板**的工具，不是破解软件。它改变的是「你机器上那份客户端对你说什么」；它不改变任何服务器、不生成任何授权凭证、不进入任何他人的系统。下面把边界逐条写死，避免任何一方误读。

**免责声明：** 本项目为非营利开源项目，仅供学习、研究与个人技术验证使用。不得用于任何违法违规用途；由此产生的全部后果由使用者自行承担。

**【零容忍】**：本项目坚决反对并严禁任何形式的违法犯罪行为。维护者绝不支持、不鼓励、不协助任何未授权网络攻击、漏洞利用、数据窃取、非法侵入计算机信息系统或生成违法违禁内容的活动。**任何将本项目用于违法犯罪的行为，均与维护者无关，由行为人依法独立承担全部法律责任。**

1. **本仓库不含违法内容，也不是破解工具。** 仓库里的代码、文档与补丁不是木马、后门、未授权渗透工具、勒索软件或撞库脚本，也不是针对公网或第三方系统的攻击载荷。
   - 本项目**不破解任何商业授权**：不生成注册码、不伪造许可证、不绕过付费墙、不一刀切掉目标软件的 license 校验、不提供任何付费功能的免费入口。
   - 本仓库 `src/` 摘除的「封条 / 激活码 / 云控下发」，是**上游对这份原本以 MIT 发布的代码自己追加的二次加锁**（时间线见 [evidence/EVIDENCE.md](evidence/EVIDENCE.md)）。在 MIT 授权下，追加封条并不产生禁止被许可人解锁的权利，理据见第 5 条。这也不是任何第三方商业软件的授权保护机制——两件事性质不同，不要混为一谈。
   - 「破甲」在此处的含义是：把一份自定义提示词写进客户端的**本机模板文件**，让模型按另一套人格与规则工作。它是提示词工程，不是二进制注入，也不涉及任何加密算法的对抗。

2. **只作用于使用者本机已安装的客户端。** 全部读写发生在你本机的安装目录与用户目录（如 `%LOCALAPPDATA%`、`~/.workbuddy`、`~/.workbuddy-ai`、目标客户端的 `resources/` 等）。对象是**你自己有权管理的本机软件**，不是他人的网站、服务器、账号、数据库或信息系统。本项目不修改任何服务端，不伪造任何请求，不代任何人操作他人设备。

3. **可逆、可回滚、可审计。** 每次改动前写入旁路备份（`.unlockbak` / `.unlockbak-ai` 等），`--revert` 一键还原；原档另有独立保险库，防止备份被宿主升级或清理工具冲掉。源码全公开、无二进制黑盒（发布的 exe 由本仓库 Actions 从同一份源码构建），任何人都能逐行核对它到底做了什么。

4. **不设后门、不上报、不常驻。**
   - 无账号体系、无登录、无遥测、无埋点、无使用统计、无云端配置下发、无静默更新。本仓库没有、也不会添加任何「回传」通道。
   - 核心流程（定位 → 备份 → 替换 → 校验 → 还原）**全程离线**，不产生任何网络请求。
   - **唯一的外部连接是可选的**：`--install-git` 会从公共镜像（npmmirror / 清华 TUNA / GitHub）下载 Git for Windows 安装包，用于补齐 DSH 在 Windows 上的依赖。该动作由使用者主动触发，且只下载、不上传，不发送任何本机信息。不需要就别用它。
   - 不写注册表自启、不装服务、不驻留后台；`--guard install` 是使用者显式发起的计划任务，可随时卸载。

5. **对上游代码的修改是 MIT 明确授权的，不是灰色地带。** 上游 `z91772524-ai/pojia-next` 以 MIT 发布其源码，而 MIT 授予的权利原文即包含 `use, copy, modify, merge, publish, distribute, sublicense`。**摘除封条属于 `modify`，是本仓库作为被许可人本就享有的权利**——不需要援引任何法定例外，也谈不上「规避技术措施」：`src/` 取自**公开源码快照**（`536ece2`），不是在 exe 上做逆向或脱壳（脱壳产物不在本仓库内，也从不分发），从头到尾没有「破解加密」这一环。MIT 授权一经授出即不可撤销，著作权人事后追加的封条、删掉的源码、改掉的口径，都不影响已经授出的修改权。MIT 唯一的实质性义务是保留版权声明与许可声明，本仓库以 `LICENSE` 双行版权 + [NOTICE](NOTICE) 范围说明完整履行。
   - 真正需要谨慎的是**另一层关系**：被修改的目标客户端（WorkBuddy、Cursor、Trae 等）是第三方商业软件，其最终用户许可协议（EULA）**可能**限制对安装文件的修改。这一层与本仓库的 MIT 授权无关，属于使用者与目标软件厂商之间的合同关系；是否接受该风险由使用者自行判断，后果可能包括账号受限或失去官方支持。
   - 本项目的定位始终是：在**自己有权管理的本机**上，调整本机软件的提示词行为；不分发任何目标客户端的副本或其修改版。
   - 维护者不为任何人提供法律意见；对具体边界有疑问，请咨询执业律师。

6. **严禁违法与违禁用途。** 使用者严禁利用本项目直接或间接从事违反下列法律法规的行为，不得以任何理由规避：
   - **《中华人民共和国刑法》**（尤其第二百八十五条非法侵入计算机信息系统罪、第二百八十六条破坏计算机信息系统罪、第二百五十三条之一侵犯公民个人信息罪）
   - **《中华人民共和国网络安全法》**（尤其第二十七条：不得从事非法侵入他人网络、干扰他人网络正常功能、窃取网络数据等危害网络安全的活动）
   - **《中华人民共和国数据安全法》《中华人民共和国个人信息保护法》《中华人民共和国著作权法》《计算机软件保护条例》**
   - 以及其他现行有效的法律、行政法规与监管规定。
   - 同时严禁：未经授权侵入、干扰或破坏公私机构的计算机信息系统；窃取、买卖、泄露他人数据与个人信息；制作、传播恶意程序；
   - **尤其严禁：借本工具解除限制后，生成或传播危害国家安全、恐怖主义、暴力血腥、涉黄涉赌、诈骗、侵权、危害未成年人等任何法律明令禁止的内容。工具解除的是客户端的内容限制，不免除使用者的任何法律责任。**
   - 同时应遵守各 AI 服务商的《服务条款》与《滥用政策》。违反可能导致账号被限制或封禁，该后果由使用者自负。

7. **使用者独立承担全部责任。** 本项目依 MIT「按现状」（AS IS）提供，不附带任何明示或暗示的担保，包括但不限于适销性、特定用途适用性与不侵权担保。使用本项目可能导致目标客户端异常、更新失效、配置损坏、账号受限或数据丢失；**使用者应对自身的下载、部署、运行、修改、传播行为以及由此产生的全部输入与输出后果，承担独立、完全的民事、行政及刑事法律责任**。维护者与贡献者不承担任何直接、间接、附带或连带责任。

8. **许可边界与滥用后果（不虚构 MIT 没有的条款）。** MIT 只设一个条件：所有副本或实质部分须保留版权声明与许可声明。除此之外，MIT **不限制用途、不限制商业使用，也没有「违约即终止」条款**——给 MIT 追加用途限制既不符合许可证原文，在许可法上也不产生效力。
   - 因此，用本项目从事违法犯罪，违反的是《刑法》《网络安全法》等**公法**，不是 MIT；后果由行为人自负，与维护者无关。维护者一旦发现此类使用，会**公开切割、拒绝提供任何支持与更新**，并在收到合法要求时配合执法机关。
   - 反过来，如果有人在再分发时**删除或隐瞒** `LICENSE` / `NOTICE` 里的版权与许可声明，那就是超出了 MIT 的授权范围，构成**版权侵权**，维护者保留追究的权利。这是 MIT 下唯一能「收回授权」的情形，也是唯一有意义的那条线。
   - 维护者不为任何第三方的修改版、收费版、换皮版提供担保或技术支持。

9. **本项目免费，但如实说明：MIT 允许他人转售。** 本项目由维护者永久免费提供：不收费、不卖激活码、不做付费版、不做「赞助换功能」。但**MIT 授予任何人再分发甚至收费转售的权利**（`distribute` / `sublicense`），只要保留版权与许可声明。本声明不否认、也无法禁止这一点。
   - 你看到有人出售本软件，**本身不构成对本项目的侵权**——前提是他保留了 `LICENSE` 与 `NOTICE`。
   - 可以追究的是这三种情形：① 删除或隐瞒版权与许可声明（版权侵权）；② 以本项目**官方**名义收费，或暗示获得维护者授权、背书（虚假宣传 / 不正当竞争）；③ 使用本项目名称与图标造成来源混淆（商标性使用）。
   - 维护者不为任何第三方收费版本提供支持、更新或退款。

10. **第三方独立性。** 本项目与 WorkBuddy / 腾讯、DeepSeek、Anthropic、OpenAI、Google、Cursor、字节跳动（Trae / CodeBuddy）、Moonshot（Kimi / Kiro）、GitHub 等**均无隶属、合作、授权或背书关系**。文中出现的产品名与商标归各自所有者，仅用于说明兼容目标，不表示任何官方认可。本项目也**不是**上游 `z91772524-ai/pojia-next` 的官方续作，仅基于其最后一版公开源码独立演进。

11. **权利人通知渠道。** 若相关权利人认为本仓库内容侵犯其合法权益，请通过仓库 Issues 或提交页所列联系方式告知，说明具体文件与权利依据。维护者核实后将立即修改或移除相关内容。本项目无意侵犯任何人的合法权益，也无意替代任何官方发行渠道。

---

## 十、证据材料

`evidence/` 里是三份独立文档，与工具本身无关，供需要溯源的人自取：

- [EVIDENCE.md](evidence/EVIDENCE.md) —— 上游 112 条提交逐条记录与关键节点
- [群聊取证.md](evidence/群聊取证.md) —— 官方群推广行为的逐条取证（QQ 号已打码）
- [反二改保护.md](evidence/反二改保护.md) —— 三层「防二改」机制拆解：技术有效，许可无效

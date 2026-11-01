# 破甲一键通 · 社区版（Community Edition）

> 仓库 `Mladery/pojia-ce`，对外版本号 **`v8.3-CE`**。
> 独立维护的社区版，源自上游最后一版**带源码**的提交（`536ece2`，v8.14）。
> MIT 协议，**非官方**，与原作者无隶属关系；本项目按自己的节奏演进，不跟随上游成品。

仓库名刻意不叫 `pojia-next`：那和上游同名，容易被当成「上游的正统续作」。这里只是社区自己维护的一份分支，`-ce` 就是 Community Edition，不主张任何继承关系。

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
| `trae` | Trae（国内版 `~/.trae`、国际版 `~/.trae-cn`，均读 `rules/project_rules.md`） |
| `codebuddy` | CodeBuddy 腾讯（`~/.codebuddy/CODEBUDDY.md`） |
| `opencode` | OpenCode（`~/.config/opencode/AGENTS.md`） |
| `windsurf` | Windsurf（`~/.codeium/windsurf/memories/global_rules.md`） |
| `cline` | Cline（`~/Documents/Cline/Rules/pojia-inject.md`） |
| `copilot` | GitHub Copilot CLI（`~/.copilot/copilot-instructions.md`） |

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
python src/破甲一键通.py --clean-spill --target wb   # 清过期的会话快照
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

守护任务（`--guard install`）两个版本一起守，写进任务的是 `--quiet --target wb,wbintl`。上游那版 `--quiet` 会把 target 无条件压成 `wb`，写什么都被覆盖，所以国际版从来没被守过。

### 2. 安装根发现增强

原来的定位链只认 `Program Files`、`LOCALAPPDATA\Programs` 和盘符根下几个固定目录名。实际装机大量是「自定义盘符 + 自定义一级目录」—— `J:\Workbuddy-GLOBAL\WorkBuddyAI`、`H:\Workbuddy`、`J:\wb\WorkBuddyManager` 都属于这一类，固定候选一个都命中不了。新增三条线索：

| 来源 | 做法 | 本机实测 |
|---|---|---|
| 进程反查 | 从运行中进程的命令行取 exe 绝对路径 | 0.00 s |
| 切换工具配置 | 在 `~/.wb-switch`、`~/.cc-switch` 的 JSON 里反查 exe 绝对路径 | 0.05–0.06 s |
| 开始菜单 / 桌面快捷方式 | 纯标准库解析 `.lnk` 目标 | 0.04–1.2 s |
| 有界目录遍历 | 按「深度优先于盘符」找 exe，8 s / 4 万条双预算 | 0.03–4.9 s |

两个配套细节：

- **互斥判据**：两版目录里都有同一份 `workbuddy-prompt.tpl`，只查模板会把国际版认成国内版。国内版新增「`WorkBuddyAI.exe` 不在场」这一条，自动发现层统一使用它。
- **来源标注**：`--status` 会显示 `← 切换工具配置` / `← 快捷方式` / `← 进程反查` / `← 目录遍历`，定位错了能立刻看出是哪一层判断的。

`.lnk` 解析是自己按 Shell Link 格式读的，不走 `WScript.Shell` —— COM 实例化在受管环境里会被安全策略直接拦掉（本机实测如此），而且每次定位都起一个 COM 对象也不值得。

**这套发现不是 WorkBuddy 专用。** `discover_app_root()` 把四个来源串成一层，按「准、快、省」排序：进程反查 → 切换工具配置 → 快捷方式 → 有界遍历（前三层都是读现成记录，只有最后要实扫盘，所以放最后，并且带 180 s 结果缓存）。DSH 和 ZCode 都接了进来 —— 它们同样有「装在哪由用户决定」的问题：DSH 要找到 `resources/app` 里的插件（以及 asar 里那份），ZCode 要找到 `resources/glm/zcode.cjs`。

Cursor / Trae / CodeBuddy / Windsurf / Claude 这几个的靶点是配置目录里的文件，安装路径帮不上忙，所以不加无意义的扫描；但「没检测到」时现在会反查一次安装目录（只走三个廉价通道，不实扫），把话说清楚：

```
!!  没检测到 Cursor（配置目录 C:\__no_such_dir__ 不存在）
    但安装目录在 H:\cursor（← 快捷方式）：启动一次 Cursor 让它生成配置目录，再重跑即可
```

**顺带修了 DSH 一个一直没发现的问题。** npm 全局装出来的布局是：

```
node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\dsh-agent-instructions\lib\index.js
```

插件比 `@deepseek-ai` 这一层低了两层，而原来的 glob 只认「插件就在 base 下面」这一种，于是**明明装了 DSH，却报「目标 0 个 / 可能 DSH 没装」**。现在每条规则都补了「隔一层 `dsh` 包」的写法，本机实测从 0 个靶点变成 7 个（1 个 js + 4 个 profile yml 可打，1 个动态身份跳过）。

### 3. 图形界面

`python src/破甲GUI.py`（或 `python src/破甲一键通.py --gui`）起一个本机网页 UI，自动打开浏览器。仍然是零第三方依赖：`http.server` + 原生 HTML/CSS，没有打包任何前端框架。它与上游发行包里那份同名文件毫无关系，见 §七。

- 选目标、点操作、看输出，输出区直接还原核心脚本的 ANSI 着色；
- 只绑 `127.0.0.1`，每次启动生成随机 token 写进地址，接口校验 —— 防止本机其他网页直接 POST 到端口触发破坏性操作；
- 破甲 / 还原在页面里二次确认，服务端再校验一次 `confirm` 字段，两道都过才执行。

用网页而不是 tkinter：ttk 主题在 Windows 上做不出圆角、阴影和过渡，网页这边几行 CSS 就够；上游早期的 GUI 也是本机网页，用户习惯一致。

### 4. 菜单交互修复

PyCharm / VSCode 运行窗口里的老问题：执行完一个操作后按空格没反应，按两次回车菜单一闪就退出。

两个原因，都堵了：

- 菜单把**空输入**当成退出（和 `0` 写在同一行）。PyCharm 控制台在 `input()` 后常残留一个 `\r\n`，用户按一次回车「返回菜单」，菜单立刻把残留换行读成空输入直接 `return`。现在空输入只重画菜单。
- 等待返回用的是 `input()`，空格不算提交，且回车会进缓冲区被下一轮吃掉。改用 `msvcrt.getwch()` 逐字符读，回车 / 空格 / Esc / q 都算，读完再清空缓冲区。

### 5. 会话快照体检

WorkBuddy 每次启动都在 `%TEMP%` 留一份自己的产品配置副本（`workbuddy-product-spill-*`，400–570 KB），正常退出才删。崩溃、强杀、直接关窗口就留在那儿 —— 本机实测堆了 173 份、约 100 MB，其中一百多份超过一天。

问题不只是占地方：**副本里原样带着产品配置的 `apiKey`**。

- `--apply` / `--check` 会报数量、体积、过期份数，用人话说清它是「程序自己留的配置复印件，删了不影响功能」；
- 顺手做一次**密钥体检**：扫副本里的明文 API Key / Bearer 令牌 / JWT / 私钥块，只输出脱敏形态和大致来源主机，**绝不打印原文**（与 `--check` 扫 Codex `config.toml` 同一口径）；
- 默认**只报不删** —— 副本不在备份范围内，删了 `--revert` 也找不回来。要清得明说：`--clean-spill` 清过期的，`--purge-spill` 全清；这两个开关单独敲就只清快照，不顺带跑一遍破甲。

TEMP 里的副本是两个版本共用的同一个目录，按副本自身的 `dataFolderName` 认领归属，否则 `--check` 会把同一批文件在 `wb` 和 `wbintl` 底下各报一遍。

### 6. DSH 0.2.1-rc.5 适配（asar 解包 + 注入点改名）

官方 DSH 桌面端升级到 `0.2.1-rc.5` 之后暴露了两个问题，都是「看起来打了、其实没打」的静默失效：

**注入点常量改名。** 身份注入靠替换官方 JS 里的 intro 常量。旧版叫 `WORKSPACE_CONTEXT_INTRO` / `REPLACEMENT_WORKSPACE_CONTEXT_INTRO`，`0.2.1-rc.5` 改成了 `AGENT_INSTRUCTIONS_INTRO` / `REPLACEMENT_AGENT_INSTRUCTIONS_INTRO` / `EMPTY_REPLACEMENT_AGENT_INSTRUCTIONS_INTRO`。旧名单只认老名字，于是新版上 `patch_intro_consts` 一个都没匹配到、`apply` 报告「已是最新」，实际一个字节没写。现在新旧五个名字全认。

**「部分已打」是假警报。** 判断「这份文件我们改过没有」原来用了 `SCOPE_REPLACEMENT` 这句文本，而 `0.2.1-rc.5` 的官方原文里本来就带 *These instructions are ACTIVE and MANDATORY for the stated scope* —— 结果任何一份没动过的官方文件都被判成「部分已打」。改用本工具自己的标记（`pojia-yijiantong` / `unlock-v6:h=` 等）当判据。

**asar 解包的三处修正。** 桌面端真正跑的插件打包在 `resources/app.asar` 里（本机 182 MB），解包到 `resources/app/` 后才能当普通文件补：

- 复用判定原来写死 `app/dsh/node_modules/@deepseek-ai` 一个路径，实际布局不符时**每次 `--check` 都重解 180 MB**（实测 `--status --target dsh` 从 4 秒变成 3 分钟跑不完）。现在两种布局都认，并且必须真的找到 `dsh-agent-instructions` 才复用；
- 每次解包用唯一 tmp 名（带 PID），改名前**硬校验插件目录确实写出来了**才 rename —— 否则宁可失败也不装一个残缺的 `resources/app/`（DSH 优先加载它，装残了桌面端直接起不来）；
- 文件句柄全程只开一次（原来每个文件开关一遍）；`unpacked` 标记但 `.unpacked/` 里缺文件的条目回落到 asar 数据区读，不再静默丢弃。

npm 全局装的和官方安装的是**两份独立拷贝**（本机实测同为 `0.2.1-rc.5`，`index.js` 字节完全一致），补一份不影响另一份，脚本会把两份都列出来分别打。

### 7. 写后自检与长路径

**写后自检。** 打完补丁立刻回读，用同一套判据复核「目标态到底成没成」；判成 `stale` / `strict` / 出错就按备份把这份文件回滚，并从清单里摘掉。原来只认「写没写成功」——写成功了、但内容不是期望态的情况（比如注入点改名导致正则没匹配上）会一路绿灯，重启后行为没变，最难查。

**长路径前缀。** npm 全局装出来的靶点动辄 `…\node_modules\@deepseek-ai\dsh\node_modules\@deepseek-ai\dsh-agent-instructions\lib\index.js`，叠一层用户目录就顶到 `MAX_PATH=260`；超了 `open()` 抛的是 `FileNotFoundError`，看着像「文件不存在」，实际是路径太长，很容易被当成「没装」而放过一整个靶点。现在超过 240 字符自动加 `\\?\` 前缀（UNC 走 `\\?\UNC\`），读写与原子替换都走这条路径。

### 8. 镜像层（第二重申）

长会话里，开头那段人格声明会被后面几十万 token 挤出「热区」，模型开始慢慢滑回默认语气。解法不是把主块写得更长（那只会让开头更早失效），而是在主块之后**不远处**再放一小块——只含覆盖声明与自证口令，**不带政策全文**。

两块各有独立标记（`POJIA-NEXT-INJECT` 与 `POJIA-CE-MIRROR`），任何一块单独存在都能工作：

- 老版本打的文件只有主块 → `--apply` 自动补上镜像层，主块不动；
- 只剩镜像层的半残文件 → `--apply` 补齐主块，`--revert` 也能认出来并整份还原；
- `--check` 会分别报「已破甲」和「镜像层在位」，缺镜像层提示重跑 `--apply`。

还原时先剥主块、再剥镜像块，两处都剥干净才算还原，所以「破了甲 → 还原」依旧能逐字节回到原样（有回归测试盯着）。

### 9. Electron 保险丝与 Trae 双发行版

**Electron 保险丝。** 桌面端把插件从 `app.asar` 解包到 `resources/app/` 之后，Electron 还可能因为内置的 `OnlyLoadAppFromAsar` 开关而**完全无视**这个目录——补丁确实写进磁盘了，程序照旧读 asar，症状是「打了跟没打一样」，而且从文件内容上完全查不出来。现在 `--apply` 先只读探测这个开关，开着就翻成关（改前留 `.pojia-fusebak`，幂等，翻过的不会重复翻）；`--check` 单独报一行，开着就判 `fail` 并说明原因。

**Trae 双发行版。** Trae 有国内版与国际版两个包，配置目录分别是 `~/.trae` 与 `~/.trae-cn`，进程名、可执行文件名都不一样。现在两个候选目录、两个环境变量、三个进程名一起找，命中哪个用哪个；装了另一版会在体检里提醒一句，避免「以为没装」。

### 10. 与上游的差异

截至 2026-11-01，与上游最新公开文档逐条比对：

| 能力 | 上游 | 本仓库 |
|---|---|---|
| WorkBuddy 国际版 | 只有 `wb` 一个目标，未区分国内版 / 国际版 | `wbintl` 独立目标 |
| 开始菜单 / 桌面快捷方式解析 | 未见 | 纯标准库 `.lnk` 解析 |
| 切换工具配置反查（wb-switch / cc-switch） | 未见 | 有 |
| 会话快照的密钥体检 | 未见 | 有（只报脱敏形态） |
| 安装目录发现 | Program Files / `LOCALAPPDATA` / 注册表 / 所有盘符 / 运行中进程 / npm | 同左，另加上面四条；且 DSH / ZCode 共用同一套发现 |
| DSH `app.asar` 内插件 | 未见（只处理磁盘上散开的文件） | 解包到 `resources/app/` 再补，带完整性硬校验 |
| DSH 0.2.1-rc.5 常量改名 | 未见 | 新旧五个 intro 常量名全认 |
| 长上下文重复注入 | 未见 | 主块 + 独立镜像块，任一在位即可 |
| Electron `OnlyLoadAppFromAsar` 保险丝 | 未见 | 自动探测并关闭，改前留备份 |
| Trae 国内版 / 国际版 | 只认一个配置目录 | `~/.trae` / `~/.trae-cn` 双候选 |
| 写后自检 | 未见 | 回读复核，不合格即按备份回滚 |
| Windows 长路径 | 未见 | 超过 240 字符自动加 `\\?\` 前缀 |
| 目标数量 | 15 | 16 |

> 保留意见：上游自 v8.14 起不再公开源码，上表依据其 README 与更新日志比对，「未见」只代表文档未声明，不等于其代码中一定没有。安装目录发现一项上游明确是有的，差异在「猜固定目录名」与「按盘符 × 深度实找」之间。

---

## 六、校验

```
342af6577925b07314dd2daefde7477ac4591511336b3b0ca02580e4dea8fcae  src/破甲一键通.py           (385,565 B / LF)
7b09ba3574f3c1728adc649c154dd5292a907eec08379edffe2adeba594a7e52  src/破甲GUI.py              (23,658 B / LF)
f470a41ac51116fd12052f8c01eecf2d08c87c26100d3c26472134b7b22a73d0  upstream/破甲一键通.v8.14.py (351,393 B / LF)
```

`src/` 下的两份随本仓库每次改动而变，上面的值对应本版；`upstream/` 是不动的锚点，可直接对着上游复核：

```bash
git clone https://github.com/z91772524-ai/pojia-next && cd pojia-next
git show 536ece2:破甲一键通.py | sha256sum
```

`src/破甲一键通.py` 现在比 `upstream/` 大 34,172 B —— §四 的「只删不加」说的是摘封条那一步；多出来的字节来自 §五 的新增功能（`wbintl`、`.lnk` 解析、快照体检、DSH 0.2.1-rc.5 适配、镜像层、保险丝探测、写后自检）。

版本号分两段存：`VERSION = "8.3"` 是写进护照和标记块的**机器值**，`EDITION = "CE"` 只拼到对外显示上（`VER_TAG = "8.3-CE"`）。把 `-CE` 塞进护照会让所有已打的靶点一夜之间变成「旧版」，全是假警报。

---

## 七、仓库内容

```
LICENSE                        上游 MIT 原文，未改动（Copyright (c) 2026 z91772524-ai）
src/破甲一键通.py               纯净版核心：摘掉 16 个加密封条函数，可直接跑
src/破甲GUI.py                  图形界面：本机网页 UI，零依赖
upstream/破甲一键通.v8.14.py    上游 536ece2 的原始核心，未改动，用于比对
evidence/                      取证材料：提交时间线、群聊记录、防二改机制拆解
```

**注意同名**：上游发行包里的 `破甲GUI.py` 和本仓库的 `src/破甲GUI.py` **只是重名，不是同一份代码**，两者没有任何继承关系。

- 上游那份绑了群号登录、激活码校验、`cloud.json` 存档、云控下发与静默更新，属成品发行侧的东西 —— 本仓库不收、不改、不兼容，也别指望拿它替换 `src/破甲GUI.py`。
- 本仓库这份是重新写的本机网页 UI：没有账号、没有激活码、不联网、不自动更新，只调本地核心脚本。要图形界面用这个就够，不必去装官方成品。

---

## 八、许可、独立性与免责

- 全部代码来自上游 `z91772524-ai/pojia-next`，版权归原作者，按 **MIT License** 使用与再分发。`LICENSE` 保留上游原文未改 —— 这是 MIT 唯一的硬性条件。本仓库自身的改动同样以 MIT 发布，不主张对原作的额外权利。
- **独立维护，不是上游的分支跟踪者。** 代码来源仅两份：`536ece2` 的快照与在此之上摘除封条的净化版。上游此后的一切成品（exe / 激活码 / 云控）与本仓库无任何代码或分发关系；本项目不追其版本号，不合并其后续提交。
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

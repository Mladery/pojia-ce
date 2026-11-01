#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
破甲一键通 · 图形界面（社区版）
================================================================================

本机网页 UI，零第三方依赖：只起一个 127.0.0.1 的 http.server，把按钮动作转成
对核心脚本的命令行调用，再把它的输出原样流回页面。

两种运行形态：
  · 源码态 —— `python src/破甲GUI.py`，每个动作拉起 `python -u 破甲一键通.py …`。
  · 打包态 —— 由单文件包里的 `--gui` 用 runpy 在核心进程内跑起来（本文件是打包时
    塞进去的数据文件）。包里没有解释器，所以每个动作直接把**自己的 exe** 当命令行，
    而 `--version` 这类要读源码的地方改成问自己一次。

为什么用网页而不是 tkinter：
  · tkinter 的 ttk 主题在 Windows 上很难做出「现代极简」的观感 —— 圆角、阴影、
    过渡都要自己用 Canvas 画；网页这边几行 CSS 就够，而且天然支持深色终端区。
  · 上游早期的 GUI 也是本机网页，用户习惯一致。
  · 仍然是零依赖：http.server / webbrowser / subprocess 全在标准库。

安全边界：
  · 只绑定 127.0.0.1，不接受外部连接；
  · 每次启动生成随机 token，页面地址带 token，接口校验 token —— 防止本机其他
    网页/程序直接 POST 到端口上触发破坏性操作；
  · 破甲 / 还原必须在页面里二次确认，服务端还会再校验一次 confirm 字段。

用法：
    python src/破甲GUI.py            # 起界面并自动打开浏览器
    python src/破甲GUI.py --no-open  # 只起服务，自己开地址
    pojia-ce.exe --gui               # 打包版（POJIA_GUI_NO_OPEN=1 可关掉自动开浏览器）
"""

import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

FROZEN = bool(getattr(sys, "frozen", False))
if FROZEN:
    # 冻结态的 __file__ 在 PyInstaller 的临时解包目录里（每次运行换一个、退出即删）。
    # 可执行文件旁边的 persona.md / 状态/ 才是"用户看得见的那份"，一律以它为基准。
    HERE = os.path.dirname(os.path.abspath(sys.executable))
    CORE = ""                      # 包里没有 .py 可跑，动作走 exe 自己
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
    CORE = os.path.join(HERE, "破甲一键通.py")
IS_WIN = (os.name == "nt")
TOKEN = secrets.token_urlsafe(18)
_VER_CACHE = []


def _spawn_flags():
    """起子进程时的 creationflags：Windows 上别弹黑框。"""
    if IS_WIN:
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def _frozen_version():
    """冻结态读不到核心源码，就问自己一句：`exe --version` 打的就是版本号。

    起自己的进程要解一次包（约一秒），所以结果缓存住 —— 一次界面会话只问一遍。
    """
    if _VER_CACHE:
        return _VER_CACHE[0]
    ver = "?"
    try:
        r = subprocess.run(
            [sys.executable, "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=180, creationflags=_spawn_flags(),
        )
        txt = (r.stdout or b"").decode("utf-8", "replace")
        m = re.search(r"(\d+\.\d+(?:-[A-Za-z0-9.]+)?)", txt)
        if m:
            ver = m.group(1)
    except Exception:              # 版本号是显示用的，问不到就显示 ?，别把界面拖崩
        pass
    _VER_CACHE.append(ver)
    return ver


def core_version():
    """从核心脚本里读版本号，免得两边写死后对不上。

    核心脚本把「数字版本」和「社区版后缀」分开存（EDITION 不参与护照比对），
    这里拼回对外展示的完整形态，例如 8.51-CE。冻结态没有源码可读，改问 exe。
    """
    if FROZEN:
        return _frozen_version()
    try:
        with open(CORE, "r", encoding="utf-8", errors="ignore") as f:
            txt = f.read()
        m = re.search(r'^VERSION\s*=\s*"([^"]+)"', txt, re.M)
        e = re.search(r'^EDITION\s*=\s*"([^"]+)"', txt, re.M)
        if m:
            return m.group(1) + ("-" + e.group(1) if e else "")
    except OSError:
        pass
    return "?"


TARGETS = [
    ("dsh", "DeepSeek Harness"),
    ("wb", "WorkBuddy"),
    ("wbintl", "WorkBuddy 国际版"),
    ("zcode", "ZCode"),
    ("codex", "Codex CLI"),
    ("cursor", "Cursor"),
    ("claude", "Claude Code"),
    ("gemini", "Gemini CLI"),
    ("qwen", "Qwen Code"),
    ("iflow", "iFlow"),
    ("trae", "Trae"),
    ("codebuddy", "CodeBuddy"),
    ("opencode", "OpenCode"),
    ("windsurf", "Windsurf"),
    ("cline", "Cline"),
    ("copilot", "Copilot CLI"),
    ("kiro", "Kiro"),
]

ACTIONS = [
    ("status", "检测状态", "只读，不改任何文件", "read"),
    ("diagnose", "诊断详情", "逐文件列出补丁与备份状态", "read"),
    ("check", "体检", "磁盘态 / 凭证 / 自证就绪", "read"),
    ("dryrun", "预演", "只显示会改什么，不落盘", "read"),
    ("apply", "破甲", "按选中目标执行修改", "write"),
    ("revert", "还原", "从备份还原成官方原版", "write"),
    ("snapshot", "生成快照", "WorkBuddy 提示词基准", "read"),
    ("compare", "对比快照", "与最新基准比对", "read"),
]


def build_cmd(action, targets):
    # 源码态：`python -u 核心.py …`，-u 让输出不攒缓冲，页面才像在实时跑。
    # 打包态：exe 自己就是核心，直接拿自己当命令行 —— 包里没有 .py 可喂给解释器。
    base = [sys.executable] if FROZEN else [sys.executable, "-u", CORE]
    t = ",".join(targets) if targets else "all"
    if action == "status":
        return base + ["--status", "--target", t]
    if action == "diagnose":
        return base + ["--diagnose", "--target", t]
    if action == "check":
        return base + ["--check"]
    if action == "dryrun":
        return base + ["--dry-run", "--apply", "--target", t]
    if action == "apply":
        return base + ["--apply", "--yes", "--target", t]
    if action == "revert":
        return base + ["--revert", "--yes", "--target", t]
    if action == "snapshot":
        return base + ["--snapshot"]
    if action == "compare":
        return base + ["--compare"]
    return None


PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>破甲一键通 · 社区版</title>
<style>
  :root{
    --bg:#f7f8fb;
    --card:#ffffff;
    --line:#e9ecf2;
    --line-strong:#dbe1ea;
    --ink:#12151c;
    --ink-2:#5a6473;
    --ink-3:#8b94a3;
    --blue:#2563eb;
    --blue-deep:#1d4ed8;
    --blue-tint:#eff4ff;
    --blue-line:#c3d7ff;
    --danger:#d0453f;
    --ok:#2f855a;
    --radius:16px;
    --shadow:0 1px 2px rgba(16,24,40,.04), 0 14px 34px -18px rgba(16,24,40,.20);
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    margin:0; color:var(--ink);
    background:
      radial-gradient(1100px 380px at 50% -12%, #e9f0ff 0%, rgba(233,240,255,0) 62%),
      var(--bg);
    font:14px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI Variable","Segoe UI",
         "PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
    -webkit-font-smoothing:antialiased; text-rendering:optimizeLegibility;
  }
  header{
    position:sticky; top:0; z-index:20;
    display:flex; align-items:center; gap:14px;
    padding:16px 32px;
    background:rgba(255,255,255,.74);
    backdrop-filter:saturate(180%) blur(14px);
    border-bottom:1px solid var(--line);
  }
  .mark{
    width:22px; height:22px; border-radius:7px; flex:none;
    background:linear-gradient(145deg,#3b82f6 0%,#1d4ed8 100%);
    box-shadow:0 2px 6px -1px rgba(37,99,235,.45), inset 0 1px 0 rgba(255,255,255,.35);
    position:relative;
  }
  .mark::after{
    content:""; position:absolute; inset:6px;
    border-radius:2px; background:rgba(255,255,255,.92);
    clip-path:polygon(0 0,100% 50%,0 100%,35% 50%);
  }
  .brand{display:flex; align-items:center; gap:11px}
  .brand h1{font-size:14.5px; font-weight:640; letter-spacing:.01em; margin:0}
  .brand .ver{font-size:11.5px; color:var(--ink-3); letter-spacing:.02em}
  .spacer{flex:1}
  .pill{
    display:inline-flex; align-items:center; gap:7px;
    padding:5px 12px; border-radius:999px;
    border:1px solid var(--line-strong); background:#fff;
    font-size:12px; color:var(--ink-2); letter-spacing:.01em;
  }
  .pill .dot{width:6px; height:6px; border-radius:50%; background:var(--ok)}
  .pill.busy{border-color:var(--blue-line); color:var(--blue-deep); background:var(--blue-tint)}
  .pill.busy .dot{background:var(--blue); animation:pulse 1.1s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.28}}

  main{
    max-width:1180px; margin:0 auto; padding:26px 32px 36px;
    display:grid; grid-template-columns:minmax(320px,360px) 1fr; gap:18px;
    align-items:stretch;
  }
  @media (max-width:900px){ main{grid-template-columns:1fr} }

  .card{
    background:var(--card); border:1px solid var(--line);
    border-radius:var(--radius); box-shadow:var(--shadow);
    overflow:hidden;
  }
  .card-head{
    display:flex; align-items:center; gap:9px;
    padding:15px 18px 11px;
  }
  .card-head h2{
    margin:0; font-size:11px; font-weight:650; letter-spacing:.1em;
    text-transform:uppercase; color:var(--ink-3);
  }
  .card-head .tick{width:4px; height:4px; border-radius:50%; background:var(--blue); flex:none}
  .card-head .meta{
    margin-left:auto; font-size:11.5px; color:var(--ink-3);
    font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
    letter-spacing:.02em;
  }
  .card-body{padding:0 16px 16px}

  .chips{display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:7px}
  .chip{
    display:inline-flex; align-items:center; gap:8px;
    padding:8px 12px 8px 10px; border-radius:10px; cursor:pointer;
    border:1px solid var(--line-strong); background:#fff;
    font-size:12.5px; color:var(--ink-2); min-width:0;
    transition:border-color .15s ease, background .15s ease, color .15s ease;
    user-select:none;
  }
  .chip:hover{border-color:#c8d0dc; color:var(--ink)}
  .chip .mark2{
    width:6px; height:6px; border-radius:50%; flex:none;
    border:1.5px solid #cfd6e0; background:transparent;
    transition:all .15s ease;
  }
  .chip[aria-pressed="true"]{
    background:var(--blue-tint); border-color:var(--blue-line); color:var(--blue-deep);
  }
  .chip[aria-pressed="true"] .mark2{background:var(--blue); border-color:var(--blue)}
  .chip .lbl{overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .chip-tools{display:flex; gap:14px; margin-top:13px; font-size:12.5px}
  .linkbtn{
    background:none; border:0; padding:0; cursor:pointer;
    color:var(--ink-3); font:inherit;
    transition:color .13s ease;
  }
  .linkbtn:hover{color:var(--blue-deep)}

  .acts{display:grid; gap:1px}
  .act{
    display:flex; align-items:center; gap:14px; width:100%;
    padding:12px 12px; border:0; border-radius:10px; cursor:pointer;
    background:none; text-align:left; font:inherit; color:inherit;
    transition:background .13s ease, color .13s ease;
  }
  .act:hover{background:var(--blue-tint)}
  .act:hover .name{color:var(--blue-deep)}
  .act:hover .arrow{color:var(--blue); transform:translateX(2px)}
  .act:active{background:#e6eeff}
  .act[disabled]{opacity:.45; cursor:not-allowed}
  .act .name{font-weight:560; min-width:84px; transition:color .13s ease}
  .act .desc{color:var(--ink-3); font-size:12.5px}
  .act .arrow{
    margin-left:auto; color:#cfd6e0; font-size:15px;
    transition:transform .15s ease, color .15s ease;
  }
  .act.danger .name{color:var(--danger)}
  .act.danger:hover{background:#fdf1f0}
  .act.danger:hover .name{color:#b93a34}
  .act.danger:hover .arrow{color:#b93a34}

  .console-card{margin-top:0; grid-column:1 / -1}
  .console-head{
    display:flex; align-items:center; gap:10px; padding:13px 18px;
    border-bottom:1px solid var(--line); background:#fff;
  }
  .console-head h2{
    margin:0; font-size:11px; font-weight:650; letter-spacing:.1em;
    text-transform:uppercase; color:var(--ink-3);
  }
  .console-head .live{
    width:6px; height:6px; border-radius:50%; background:#cfd6e0; flex:none;
    transition:background .2s ease;
  }
  .console-head.on .live{background:var(--blue); animation:pulse 1.1s ease-in-out infinite}
  .console-head .meta{
    font-size:11.5px; color:var(--ink-3);
    font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
  }
  .console-head .spacer{flex:1}
  pre#out{
    margin:0; padding:18px 20px 20px;
    min-height:190px; max-height:44vh; overflow:auto;
    background:linear-gradient(180deg,#0d1424 0%,#0b111e 100%);
    color:#c9d4e7;
    font:12.5px/1.74 ui-monospace,SFMono-Regular,Menlo,Consolas,"Cascadia Mono",monospace;
    white-space:pre-wrap; word-break:break-word;
    tab-size:2;
  }
  pre#out::-webkit-scrollbar{width:10px; height:10px}
  pre#out::-webkit-scrollbar-thumb{background:#243049; border-radius:6px; border:2px solid #0d1424}
  pre#out::-webkit-scrollbar-thumb:hover{background:#31405e}
  pre#out .dim{color:#6b7686}
  .empty{color:#4d5871}

  .modal{
    position:fixed; inset:0; display:none; place-items:center;
    background:rgba(18,21,28,.34); backdrop-filter:blur(4px); z-index:50;
  }
  .modal.on{display:grid}
  .modal .box{
    width:min(430px,92vw); background:#fff; border-radius:18px;
    padding:26px; box-shadow:0 30px 70px -24px rgba(16,24,40,.45);
    animation:pop .16s ease-out;
  }
  @keyframes pop{from{transform:translateY(6px) scale(.99); opacity:0}to{transform:none; opacity:1}}
  .modal h3{margin:0 0 8px; font-size:15.5px; letter-spacing:.01em}
  .modal p{margin:0 0 22px; color:var(--ink-2); font-size:13.5px}
  .modal .row{display:flex; gap:9px; justify-content:flex-end}
  .btn{
    padding:9px 17px; border-radius:10px; border:1px solid var(--line-strong);
    background:#fff; font:inherit; font-size:13px; cursor:pointer; color:var(--ink);
    transition:all .13s ease;
  }
  .btn:hover{background:#f4f6fa; border-color:#c8d0dc}
  .btn.primary{
    background:linear-gradient(180deg,#3b82f6,#2563eb);
    border-color:#2563eb; color:#fff;
    box-shadow:0 1px 2px rgba(37,99,235,.35), inset 0 1px 0 rgba(255,255,255,.18);
  }
  .btn.primary:hover{filter:brightness(1.05)}
  .btn.danger{
    background:linear-gradient(180deg,#dc5a54,#c9403a);
    border-color:#c9403a; color:#fff;
    box-shadow:0 1px 2px rgba(201,64,58,.3), inset 0 1px 0 rgba(255,255,255,.16);
  }
  .btn.danger:hover{filter:brightness(1.05)}
  footer{
    max-width:1180px; margin:0 auto; padding:0 32px 34px;
    color:var(--ink-3); font-size:12px; letter-spacing:.01em;
  }
  footer b{font-weight:560; color:var(--ink-2)}
</style>
</head>
<body>
<header>
  <div class="brand">
    <div class="mark"></div>
    <h1>破甲一键通</h1>
    <span class="ver">v__VERSION__</span>
  </div>
  <div class="spacer"></div>
  <div class="pill" id="state"><span class="dot"></span><span id="state-text">就绪</span></div>
</header>

<main>
  <section class="card">
    <div class="card-head"><span class="tick"></span><h2>目标</h2><span class="meta" id="count"></span></div>
    <div class="card-body">
      <div class="chips" id="chips"></div>
      <div class="chip-tools">
        <button class="linkbtn" id="all">全选</button>
        <button class="linkbtn" id="none">全不选</button>
      </div>
    </div>
  </section>

  <section class="card">
    <div class="card-head"><span class="tick"></span><h2>操作</h2></div>
    <div class="card-body"><div class="acts" id="acts"></div></div>
  </section>

  <section class="card console-card">
    <div class="console-head" id="console-head">
      <span class="live"></span><h2>输出</h2>
      <span class="meta" id="elapsed"></span>
      <div class="spacer"></div>
      <button class="linkbtn" id="clear">清空</button>
    </div>
    <pre id="out"><span class="empty">等待操作…</span></pre>
  </section>
</main>

<footer>本地运行，仅绑定 <b>127.0.0.1</b>。破坏性操作需二次确认，所有改动均可用「还原」回退。</footer>

<div class="modal" id="modal">
  <div class="box">
    <h3 id="m-title">确认操作</h3>
    <p id="m-desc"></p>
    <div class="row">
      <button class="btn" id="m-cancel">取消</button>
      <button class="btn danger" id="m-ok">确认执行</button>
    </div>
  </div>
</div>

<script>
const TOKEN = "__TOKEN__";
const TARGETS = __TARGETS__;
const ACTIONS = __ACTIONS__;
const selected = new Set(TARGETS.map(t => t[0]));

const chipsEl = document.getElementById("chips");
const actsEl = document.getElementById("acts");
const outEl = document.getElementById("out");
const stateEl = document.getElementById("state");
const stateText = document.getElementById("state-text");
const countEl = document.getElementById("count");
const elapsedEl = document.getElementById("elapsed");
const consoleHead = document.getElementById("console-head");

TARGETS.forEach(([key, label]) => {
  const b = document.createElement("button");
  b.className = "chip";
  b.setAttribute("aria-pressed", "true");
  b.innerHTML = `<span class="mark2"></span><span class="lbl">${label}</span>`;
  b.title = key;
  b.onclick = () => {
    if (selected.has(key)) selected.delete(key); else selected.add(key);
    b.setAttribute("aria-pressed", selected.has(key));
    updateCount();
  };
  chipsEl.appendChild(b);
});

function updateCount(){ countEl.textContent = `${selected.size} / ${TARGETS.length}`; }
updateCount();

document.getElementById("all").onclick = () => {
  TARGETS.forEach(t => selected.add(t[0]));
  [...chipsEl.children].forEach(c => c.setAttribute("aria-pressed", "true"));
  updateCount();
};
document.getElementById("none").onclick = () => {
  selected.clear();
  [...chipsEl.children].forEach(c => c.setAttribute("aria-pressed", "false"));
  updateCount();
};

let busy = false;
ACTIONS.forEach(([key, name, desc, kind]) => {
  const b = document.createElement("button");
  b.className = "act" + (kind === "write" ? " danger" : "");
  b.innerHTML = `<span class="name">${name}</span><span class="desc">${desc}</span><span class="arrow">›</span>`;
  b.onclick = () => {
    if (busy) return;
    if (kind === "write") confirmRun(key, name);
    else run(key);
  };
  actsEl.appendChild(b);
});

const modal = document.getElementById("modal");
let pending = null;
function confirmRun(key, name){
  pending = key;
  document.getElementById("m-title").textContent = `确认${name}？`;
  const list = [...selected];
  document.getElementById("m-desc").textContent = list.length
    ? `将对 ${list.join(" / ")} 执行${name}。这会修改目标软件的文件，可用「还原」回退。`
    : `未选择任何目标，将按 all 处理。这会修改目标软件的文件，可用「还原」回退。`;
  modal.classList.add("on");
}
document.getElementById("m-cancel").onclick = () => { modal.classList.remove("on"); pending = null; };
document.getElementById("m-ok").onclick = () => {
  modal.classList.remove("on");
  if (pending) run(pending);
  pending = null;
};

document.getElementById("clear").onclick = () => {
  outEl.innerHTML = '<span class="empty">等待操作…</span>';
  elapsedEl.textContent = "";
};

const ANSI = {
  "30":"#6b7686","31":"#e5807b","32":"#7ec699","33":"#e6c07b","34":"#82b7e8",
  "35":"#c39ae0","36":"#79c9d1","37":"#c9d4e7","90":"#6b7686","91":"#e5807b",
  "92":"#7ec699","93":"#e6c07b","94":"#82b7e8","95":"#c39ae0","96":"#79c9d1","97":"#ffffff"
};
function esc(s){ return s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function ansiToHtml(line){
  let out = "", open = 0;
  const re = /\x1b\[([0-9;]*)m/g;
  let last = 0, m;
  while ((m = re.exec(line)) !== null){
    out += esc(line.slice(last, m.index));
    last = m.index + m[0].length;
    const codes = m[1].split(";").filter(Boolean);
    if (!codes.length || codes.includes("0")){
      out += "</span>".repeat(open); open = 0;
      continue;
    }
    for (const c of codes){
      const color = ANSI[c];
      if (color){ out += `<span style="color:${color}">`; open++; }
      else if (c === "1"){ out += `<span style="font-weight:600">`; open++; }
    }
  }
  out += esc(line.slice(last));
  out += "</span>".repeat(open);
  return out;
}

let firstChunk = true;
async function run(action){
  if (busy) return;
  busy = true;
  stateEl.classList.add("busy");
  stateText.textContent = "运行中";
  consoleHead.classList.add("on");
  if (firstChunk){ outEl.innerHTML = ""; firstChunk = false; }
  const t0 = Date.now();
  const timer = setInterval(() => {
    elapsedEl.textContent = ((Date.now() - t0) / 1000).toFixed(1) + "s";
  }, 100);

  try{
    const res = await fetch(`/api/run?t=${TOKEN}`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({action, targets: [...selected], confirm: true})
    });
    if (!res.ok || !res.body){
      outEl.insertAdjacentHTML("beforeend", `<span style="color:#e5807b">请求失败：HTTP ${res.status}</span>\n`);
    } else {
      const reader = res.body.getReader();
      const dec = new TextDecoder("utf-8");
      let buf = "";
      while (true){
        const {done, value} = await reader.read();
        if (done) break;
        buf += dec.decode(value, {stream: true});
        const parts = buf.split("\n");
        buf = parts.pop();
        for (const p of parts) outEl.insertAdjacentHTML("beforeend", ansiToHtml(p) + "\n");
        outEl.scrollTop = outEl.scrollHeight;
      }
      if (buf) outEl.insertAdjacentHTML("beforeend", ansiToHtml(buf) + "\n");
    }
  }catch(e){
    outEl.insertAdjacentHTML("beforeend", `<span style="color:#e5807b">${esc(String(e))}</span>\n`);
  }finally{
    clearInterval(timer);
    busy = false;
    stateEl.classList.remove("busy");
    stateText.textContent = "就绪";
    consoleHead.classList.remove("on");
    outEl.scrollTop = outEl.scrollHeight;
  }
}
</script>
</body>
</html>
"""


def render_page():
    return (PAGE
            .replace("__VERSION__", core_version())
            .replace("__TOKEN__", TOKEN)
            .replace("__TARGETS__", json.dumps(TARGETS, ensure_ascii=False))
            .replace("__ACTIONS__", json.dumps(ACTIONS, ensure_ascii=False)))


class Handler(BaseHTTPRequestHandler):
    server_version = "PojiaGUI"

    def log_message(self, fmt, *a):          # 静音：控制台只留自己的提示
        pass

    def _authorized(self):
        q = self.path.split("t=", 1)
        return len(q) == 2 and q[1].split("&")[0] == TOKEN

    def do_GET(self):
        if not self._authorized():
            self.send_error(403, "bad token")
            return
        body = render_page().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not self._authorized():
            self.send_error(403, "bad token")
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n) or b"{}")
        except (ValueError, OSError):
            payload = {}
        action = payload.get("action") or ""
        targets = payload.get("targets") or []
        if not isinstance(targets, list):
            targets = []
        targets = [t for t in targets if t in dict(TARGETS)]
        cmd = build_cmd(action, targets)
        if not cmd:
            self.send_error(400, "bad action")
            return
        if action in ("apply", "revert") and not payload.get("confirm"):
            self.send_error(400, "confirm required")
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        # 源码态的 cwd 是仓库根（HERE 的上一层），相对路径按项目根算；打包态没有
        # 「项目根」这回事，就落在 exe 旁边 —— 人格文件、状态目录都在那儿。
        cwd = HERE if FROZEN else (os.path.dirname(HERE) or HERE)
        try:
            proc = subprocess.Popen(
                cmd, cwd=cwd, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                bufsize=0, creationflags=_spawn_flags(),
            )
        except OSError as e:
            self.wfile.write(("启动失败：%s\n" % e).encode("utf-8"))
            return
        try:
            while True:
                chunk = proc.stdout.readline()
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            proc.kill()
        finally:
            try:
                proc.stdout.close()
            except Exception:
                pass
            proc.wait()


def main():
    if not FROZEN and not os.path.isfile(CORE):
        print("找不到核心脚本：%s" % CORE)
        return 1
    host = "127.0.0.1"
    srv = ThreadingHTTPServer((host, 0), Handler)
    port = srv.server_address[1]
    url = "http://%s:%d/?t=%s" % (host, port, TOKEN)
    # flush=True：打包态的启动脚本/CI 靠读这几行判断「界面起来了」，不刷就卡在缓冲里。
    print("=" * 66, flush=True)
    print(" 破甲一键通 · 图形界面   v%s%s"
          % (core_version(), "（打包版）" if FROZEN else ""), flush=True)
    print(" 地址：%s" % url, flush=True)
    print(" 关闭窗口或按 Ctrl+C 退出", flush=True)
    print("=" * 66, flush=True)
    # 关掉自动开浏览器：--no-open（源码态），或 POJIA_GUI_NO_OPEN=1（打包态没地方塞参数）
    quiet_open = ("--no-open" in sys.argv) or os.environ.get("POJIA_GUI_NO_OPEN")
    if not quiet_open:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n已退出。")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

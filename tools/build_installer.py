#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 onedir 产物打成一个 Windows 安装程序（setup.exe）。

为什么单独一个脚本：makensis 的 `/D` 宏必须出现在脚本路径**之前**，而且值里带
空格时要自己加引号；顺带把「makensis 到底装在哪」这件事收在一处 —— CI 上是
choco/scoop 装的，用户本机可能压根没装。

产物默认落在 `out/<name>-windows-x64-setup.exe`，和裸 exe 用同一个名字规则，
`--update` 起来之后只认这一个。

用法：
    python tools/build_installer.py --src build/dist-onedir/pojia-ce
    python tools/build_installer.py --src build/dist-onedir/pojia-ce --version 8.63
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NSI = os.path.join(ROOT, "tools", "installer.nsi")

# makensis 不在 PATH 上是常态：choco 装到 Program Files，scoop 装到用户目录。
CANDIDATES = [
    r"C:\Program Files (x86)\NSIS\makensis.exe",
    r"C:\Program Files\NSIS\makensis.exe",
    os.path.expanduser(r"~\scoop\apps\nsis\current\makensis.exe"),
    os.path.expanduser(r"~\scoop\shims\makensis.exe"),
    "/usr/bin/makensis",
    "/usr/local/bin/makensis",
]


def find_makensis():
    p = shutil.which("makensis")
    if p:
        return p
    for c in CANDIDATES:
        if os.path.isfile(c):
            return c
    return ""


def core_version():
    """从源码读 VERSION，省得版本号在三个地方各写一遍。"""
    path = os.path.join(ROOT, "src", "破甲一键通.py")
    with open(path, encoding="utf-8", errors="replace") as f:
        m = re.search(r'^VERSION\s*=\s*"([^"]+)"', f.read(), re.M)
    return m.group(1) if m else "0.0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.path.join("build", "dist-onedir", "pojia-ce"),
                    help="onedir 产物目录（含 pojia-ce.exe 与 _internal/）")
    ap.add_argument("--out", default=os.path.join("out", "pojia-ce-windows-x64-setup.exe"))
    ap.add_argument("--version", default="", help="默认取源码里的 VERSION")
    ap.add_argument("--makensis", default="", help="指定 makensis 路径")
    a = ap.parse_args()

    src = os.path.abspath(a.src)
    exe = os.path.join(src, "pojia-ce.exe")
    if not os.path.isfile(exe):
        print("没有找到 onedir 产物：%s" % exe, file=sys.stderr)
        return 1
    if not os.path.isdir(os.path.join(src, "_internal")):
        print("警告：%s 下没有 _internal/，装出来可能起不来" % src, file=sys.stderr)

    mk = a.makensis or find_makensis()
    if not mk:
        print("找不到 makensis。装一个：choco install nsis / scoop install nsis", file=sys.stderr)
        return 1

    ver = a.version or core_version()
    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # /D 的值不能加引号（makensis 会连引号一起当值），所以路径里有空格就过不去。
    for label, val in (("SRCDIR", src), ("OUTFILE", out)):
        if " " in val:
            print("%s 里有空格，makensis 的 /D 吃不下：%s" % (label, val), file=sys.stderr)
            return 1

    cmd = [mk, "/V2",
           "/DVERSION=%s" % ver,
           "/DSRCDIR=%s" % src,
           "/DOUTFILE=%s" % out,
           NSI]
    print("+ %s" % " ".join(cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("makensis 失败，退出码 %d" % r.returncode, file=sys.stderr)
        return r.returncode

    if not os.path.isfile(out) or os.path.getsize(out) < 1024 * 1024:
        print("产物不对劲：%s" % out, file=sys.stderr)
        return 1
    print("setup: %s（%.1f MB，版本 %s）" % (out, os.path.getsize(out) / 1048576.0, ver))
    return 0


if __name__ == "__main__":
    sys.exit(main())

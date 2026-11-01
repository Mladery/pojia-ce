# -*- coding: utf-8 -*-
"""Electron 保险丝（OnlyLoadAppFromAsar）的定位 / 翻转 / 备份 / 幂等。

用合成的 fuse wire 测，不碰任何真实安装：熔丝开着 = 解包出来的
resources/app/ 会被 Electron 完全无视，补丁看着打上了、其实永远不生效。
"""
import os

import pytest

WIRE_VERSION = 1


def make_fuse_blob(sentinel, flags):
    """按官方格式造一段：sentinel + version(1) + length(1) + 每位 1 字节。"""
    body = bytes([WIRE_VERSION, len(flags)]) + bytes(0x31 if f else 0x30 for f in flags)
    return b"\x00" * 100 + sentinel + body + b"\x00" * 100


@pytest.fixture()
def fuse_env(core, tmp_path):
    """造一个假的安装根：一个带熔丝的 exe + 一个无关 exe。"""
    T = core.DshTarget
    flags = [0, 0, 1, 0, 0, 1, 0]          # 第 5 位 = OnlyLoadAppFromAsar，开着
    exe = tmp_path / "Fake.exe"
    exe.write_bytes(make_fuse_blob(T._FUSE_SENTINEL, flags))
    plain = tmp_path / "Plain.exe"
    plain.write_bytes(b"\x00" * 500)
    return T, str(tmp_path), str(exe), str(plain)


def test_detects_fuse_on(fuse_env):
    T, root, exe, _ = fuse_env
    assert T.fuse_state(root).get("Fake.exe") == "on"


def test_flip_turns_it_off(fuse_env):
    T, root, exe, _ = fuse_env
    assert T._flip_only_asar_fuse(root) == 1
    assert T.fuse_state(root).get("Fake.exe") == "off"


def test_flip_leaves_backup(fuse_env):
    T, root, exe, _ = fuse_env
    before = open(exe, "rb").read()
    T._flip_only_asar_fuse(root)
    bak = exe + ".pojia-fusebak"
    assert os.path.exists(bak), "改前没留备份"
    assert open(bak, "rb").read() == before


def test_flip_is_idempotent(fuse_env):
    T, root, exe, _ = fuse_env
    assert T._flip_only_asar_fuse(root) == 1
    assert T._flip_only_asar_fuse(root) == 0, "第二次还在翻，不幂等"


def test_flip_touches_only_target_bit(fuse_env):
    """翻一位不能顺手把别的熔丝也改了 —— 那些位可能是别的功能开关。"""
    T, root, exe, _ = fuse_env
    before = open(exe, "rb").read()
    T._flip_only_asar_fuse(root)
    after = open(exe, "rb").read()
    assert len(before) == len(after)
    i = before.find(T._FUSE_SENTINEL) + len(T._FUSE_SENTINEL) + 2
    diff = [k for k in range(len(before)) if before[k] != after[k]]
    assert diff == [i + T._FUSE_ONLY_ASAR_IDX], "改到了目标位以外的字节"


def test_file_without_sentinel_untouched(fuse_env):
    T, root, _exe, plain = fuse_env
    before = open(plain, "rb").read()
    T._flip_only_asar_fuse(root)
    assert open(plain, "rb").read() == before


def test_already_off_is_not_reported_as_on(core, tmp_path):
    T = core.DshTarget
    exe = tmp_path / "Off.exe"
    exe.write_bytes(make_fuse_blob(T._FUSE_SENTINEL, [0] * 7))
    assert T.fuse_state(str(tmp_path)).get("Off.exe") == "off"
    assert T._flip_only_asar_fuse(str(tmp_path)) == 0


def test_missing_dir_is_safe(core):
    T = core.DshTarget
    assert T.fuse_state("/nonexistent/pojia/xyz") == {}
    assert T._flip_only_asar_fuse("/nonexistent/pojia/xyz") == 0

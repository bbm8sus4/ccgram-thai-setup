#!/usr/bin/env python3
"""Re-runnable structural tuning patch for ccgram (single-user phone deployment).

ทำอะไร (ทุก patch idempotent + py_compile + rollback ต่อไฟล์):
  1. cc_commands.py     : ตัด command menu 52 -> 9 (ไทย), เอา 37 '↗' ออก
  2. main.py            : แก้ bug CCGRAM_LOG_LEVEL ไม่ทำงาน (โหลด .env ก่อน + filtering logger)
  3. topic_lifecycle.py : probe ทนต่อการไม่มีสิทธิ์ pin (ไม่ spam log / ไม่ค้าง)
  4. directory_callbacks.py : CCGRAM_QUICK_START=1 -> เปิด session = Claude+YOLO ทันที ข้าม picker
  5. sessions_dashboard.py  : ปุ่ม 'เปิด session ใหม่' ที่เคย no-op -> สร้าง topic จริง

รันหลัง `uv tool upgrade ccgram` ทุกครั้ง:  python3 ~/.ccgram/ccgram-tune.py
ลำดับ: (a) ccgram upgrade (b) thai-ui-patch.py (c) ccgram-tune.py (d) restart
ย้อนกลับ: คืนไฟล์ .bak-tune แล้ว restart
"""
import re
import glob
import pathlib
import py_compile

# dynamic: รอด python version เปลี่ยนตอน uv tool upgrade
_cands = sorted(glob.glob(str(pathlib.Path.home() / ".local/share/uv/tools/ccgram/lib/python*/site-packages/ccgram")))
PKG = pathlib.Path(_cands[-1]) if _cands else pathlib.Path.home() / ".local/share/uv/tools/ccgram/lib/python3.14/site-packages/ccgram"


def apply(relpath, transform):
    f = PKG / relpath
    original = f.read_text(encoding="utf-8")
    patched = transform(original)
    if patched == original:
        print(f"  = {relpath}: already patched / nothing to do")
        return
    bak = f.with_suffix(f.suffix + ".bak-tune")
    if not bak.exists():
        bak.write_text(original, encoding="utf-8")
    f.write_text(patched, encoding="utf-8")
    try:
        py_compile.compile(str(f), doraise=True)
        print(f"  ✓ {relpath}: patched OK")
    except py_compile.PyCompileError as e:
        f.write_text(original, encoding="utf-8")
        print(f"  !! {relpath}: ROLLBACK (syntax) {e}")


# ---------- 1) cc_commands.py : trim menu ----------
NEW_BOT_CMDS = (
    "_BOT_COMMANDS: list[tuple[str, str]] = [\n"
    '    ("start", "เริ่มต้น / วิธีใช้"),\n'
    '    ("sessions", "ดู session ทั้งหมด"),\n'
    '    ("resume", "เปิด session เก่าต่อ"),\n'
    '    ("screenshot", "ภาพหน้าจอ terminal"),\n'
    '    ("live", "ดูจอ terminal สด"),\n'
    '    ("toolbar", "ปุ่มลัด / ควบคุม"),\n'
    '    ("sync", "ซ่อมสถานะ"),\n'
    '    ("restore", "กู้หัวข้อที่ค้าง"),\n'
    '    ("upgrade", "อัปเดต ccgram"),\n'
    "]"
)


def patch_cc(s):
    if "CC_BUILTINS: dict[str, str] = {}" in s:
        return s
    s = re.sub(r"CC_BUILTINS: dict\[str, str\] = \{.*?\n\}",
               "CC_BUILTINS: dict[str, str] = {}", s, flags=re.DOTALL)
    s = re.sub(r"_BOT_COMMANDS: list\[tuple\[str, str\]\] = \[.*?\n\]",
               NEW_BOT_CMDS, s, flags=re.DOTALL)
    return s


# ---------- 2) main.py : log level fix ----------
def patch_main(s):
    s = s.replace(
        "        wrapper_class=structlog.stdlib.BoundLogger,",
        "        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),",
    )
    old = '    log_level = (os.environ.get("CCGRAM_LOG_LEVEL") or "INFO").upper()'
    if "load_dotenv as _ld" not in s and old in s:
        new = (
            "    from pathlib import Path as _P\n"
            "    from dotenv import load_dotenv as _ld\n"
            '    _ld(_P.home() / ".ccgram" / ".env")\n'
            + old
        )
        s = s.replace(old, new, 1)
    return s


# ---------- 3) topic_lifecycle.py : pin-resilient probe ----------
def patch_probe(s):
    if "bot lacks pin rights" in s:
        return s  # already patched — idempotent guard (NEW contains OLD else-block)
    if "_probe_pin_disabled" not in s:
        s = s.replace(
            "async def probe_topic_existence(client: TelegramClient) -> None:",
            "_probe_pin_disabled: set = set()\n\n\nasync def probe_topic_existence(client: TelegramClient) -> None:",
            1,
        )
    s = s.replace(
        "    for user_id, thread_id, wid in list(thread_router.iter_thread_bindings()):\n"
        "        if lifecycle_strategy.should_skip_probe(wid):\n"
        "            continue",
        "    for user_id, thread_id, wid in list(thread_router.iter_thread_bindings()):\n"
        "        if wid in _probe_pin_disabled:\n"
        "            continue\n"
        "        if lifecycle_strategy.should_skip_probe(wid):\n"
        "            continue",
        1,
    )
    s = s.replace(
        "            else:\n"
        "                lifecycle_strategy.record_probe_failure(wid)",
        '            elif isinstance(e, BadRequest) and "Not enough rights" in e.message:\n'
        "                if wid not in _probe_pin_disabled:\n"
        "                    _probe_pin_disabled.add(wid)\n"
        '                    logger.info("Topic probe disabled for %s: bot lacks pin rights", wid)\n'
        "            else:\n"
        "                lifecycle_strategy.record_probe_failure(wid)",
        1,
    )
    return s


# ---------- 4) directory_callbacks.py : quick-start ----------
def patch_quickstart(s):
    # EDIT B: bypass worktree picker under quick-start
    s = s.replace(
        "    if eligibility.eligible and eligibility.repo_path is not None:\n"
        "        if context.user_data is not None:",
        "    import os as _qs_os2\n"
        "    if (\n"
        "        eligibility.eligible\n"
        "        and eligibility.repo_path is not None\n"
        '        and _qs_os2.getenv("CCGRAM_QUICK_START") != "1"\n'
        "    ):\n"
        "        if context.user_data is not None:",
        1,
    )
    # EDIT A: skip provider+mode pickers under quick-start
    s = s.replace(
        "    # Show provider selection keyboard (keep browse state for _handle_provider_select)\n"
        "    await _show_provider_picker(query, selected_path)",
        "    # Show provider selection keyboard (keep browse state for _handle_provider_select)\n"
        "    import os as _qs_os\n"
        '    if _qs_os.getenv("CCGRAM_QUICK_START") == "1":\n'
        "        from ...config import config as _qs_cfg\n"
        "        clear_browse_state(context.user_data)\n"
        "        await _create_window_and_bind(\n"
        '            query, user_id, selected_path, _qs_cfg.provider_name, "yolo", context\n'
        "        )\n"
        "        return\n"
        "    await _show_provider_picker(query, selected_path)",
        1,
    )
    return s


# ---------- 5) sessions_dashboard.py : rewire New Session button ----------
def patch_newbtn(s):
    return s.replace(
        '    elif data == CB_SESSIONS_NEW:\n'
        '        await query.answer("สร้างหัวข้อใหม่เพื่อเริ่ม session")',
        '    elif data == CB_SESSIONS_NEW:\n'
        '        try:\n'
        '            await PTBTelegramClient(context.bot).create_forum_topic(\n'
        '                chat_id=config.group_id, name="งานใหม่"\n'
        '            )\n'
        '            await query.answer(\n'
        '                "✅ สร้างหัวข้อ \'งานใหม่\' แล้ว — เปิดหัวข้อนั้นแล้วพิมพ์ข้อความเพื่อเริ่ม",\n'
        '                show_alert=True,\n'
        '            )\n'
        '        except Exception:\n'
        '            logger.exception("CB_SESSIONS_NEW create_forum_topic failed")\n'
        '            await query.answer(\n'
        '                "สร้างหัวข้อไม่สำเร็จ ลองสร้างหัวข้อใหม่เองในกลุ่ม", show_alert=True\n'
        '            )',
        1,
    )


# ---------- 6) text_handler.py : ล็อก new-session ให้เริ่มที่ CCGRAM_QUICK_START_DIR เสมอ ----------
def patch_fixed_dir(s):
    # ข้าม window picker เมื่อมี fixed dir (topic ใหม่ = สร้าง session ใหม่ในโฟลเดอร์นั้นเสมอ)
    s = s.replace(
        "    if unbound:\n"
        "        logger.info(\n"
        '            "Unbound topic: showing window picker',
        "    import os as _qs_os\n"
        '    if unbound and not _qs_os.environ.get("CCGRAM_QUICK_START_DIR"):\n'
        "        logger.info(\n"
        '            "Unbound topic: showing window picker',
        1,
    )
    # ล็อก root ของ directory browser ให้เป็น CCGRAM_QUICK_START_DIR (ถ้าตั้งไว้ + มีจริง)
    s = s.replace(
        "    start_path = str(Path.cwd())\n"
        "    msg_text, keyboard, subdirs = build_directory_browser(start_path, user_id=user_id)",
        '    import os as _qs_os2\n'
        '    _qs_dir = _qs_os2.environ.get("CCGRAM_QUICK_START_DIR", "")\n'
        "    start_path = _qs_dir if (_qs_dir and Path(_qs_dir).is_dir()) else str(Path.cwd())\n"
        "    msg_text, keyboard, subdirs = build_directory_browser(start_path, user_id=user_id)",
        1,
    )
    return s


# ---------- 7) toolbar_config.py : ตัด toolbar เหลือ 2 แถวจำเป็น ----------
_TB_MIN = (
    '            ("screen", "live", "esc"),\n'
    '            ("up", "enter", "down"),'
)
_TB_OLD = {
    "claude": (
        '            ("screen", "ctrlc", "live"),\n'
        '            ("mode", "think", "esc"),\n'
        '            ("up", "enter", "down"),\n'
        '            ("last", "getfile", "close"),'
    ),
    "codex": (
        '            ("screen", "ctrlc", "live"),\n'
        '            ("esc", "tab", "mode"),\n'
        '            ("up", "enter", "down"),\n'
        '            ("last", "getfile", "close"),'
    ),
    "gemini": (
        '            ("screen", "ctrlc", "live"),\n'
        '            ("mode", "yolo", "esc"),\n'
        '            ("up", "enter", "down"),\n'
        '            ("last", "getfile", "close"),'
    ),
    "pi": (
        '            ("screen", "ctrlc", "live"),\n'
        '            ("esc", "tab", "model"),\n'
        '            ("up", "enter", "down"),\n'
        '            ("last", "getfile", "close"),'
    ),
    "shell": (
        '            ("screen", "ctrlc", "live"),\n'
        '            ("enter", "eof", "susp"),\n'
        '            ("last", "getfile", "esc", "close"),'
    ),
}


def patch_toolbar(s):
    for _prov, old in _TB_OLD.items():
        s = s.replace(old, _TB_MIN, 1)
    return s


# ---------- 8) ปิด 🤔 reaction (รก แปะหน้าคิดบนข้อความ user) ----------
def patch_react(s):
    # ปิด 🤔 ในระบบ react ทั่วไป (เก็บ ⚡/🔥/💔 ไว้)
    if 'if emoji == "\U0001f914"' in s:
        return s  # idempotent guard (NEW contains OLD anchor)
    s = s.replace(
        "    if emoji not in ALLOWED_REACTIONS:",
        '    if emoji == "\U0001f914":\n'
        "        return True\n"
        "    if emoji not in ALLOWED_REACTIONS:",
        1,
    )
    return s


def patch_react_general(s):
    # ปิด 🤔 ใน General topic
    s = s.replace(
        "        with contextlib.suppress(TelegramError):\n"
        '            await message.set_reaction("\U0001f914")',
        "        with contextlib.suppress(TelegramError):\n"
        "            pass  # 🤔 reaction disabled (noise)",
        1,
    )
    return s


# ---------- 9) Get File: กดทีเดียวส่งไฟล์ล่าสุด (ไม่เปิด browser) ----------
def patch_getfile(s):
    old = (
        "    # Lazy: send subpackage ↔ status_bar_actions cycle\n"
        "    from ..send import open_file_browser\n"
        "\n"
        "    await open_file_browser(\n"
        "        PTBTelegramClient(query.get_bot()),\n"
        "        chat_id,\n"
        "        thread_id,\n"
        "        context.user_data,\n"
        "        window_id,\n"
        "        cwd,\n"
        "    )\n"
        "    await query.answer()"
    )
    new = (
        "    # one-tap: ส่งไฟล์ล่าสุดในโฟลเดอร์ session ตรงๆ (ไม่เปิด browser)\n"
        "    import os as _gf_os\n"
        "    from ..send.send_command import upload_file as _gf_upload\n"
        "    _GF_RICH = ('.pdf', '.html', '.htm', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.csv', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.zip', '.rar', '.7z', '.mp4', '.mov', '.mp3', '.wav', '.m4a', '.epub')\n"
        "    _GF_TEXT = ('.txt', '.md', '.rtf')\n"
        "    _GF_NOISE = ('.json', '.jsonl', '.lock', '.log', '.pyc', '.pyo', '.tmp', '.swp', '.bak', '.pid')\n"
        "    _gf_rich = None\n"
        "    _gf_rich_mt = -1.0\n"
        "    _gf_text = None\n"
        "    _gf_text_mt = -1.0\n"
        "    _gf_any = None\n"
        "    _gf_any_mt = -1.0\n"
        "    for _gf_root, _gf_dirs, _gf_files in _gf_os.walk(cwd):\n"
        "        _gf_dirs[:] = [_d for _d in _gf_dirs if not _d.startswith('.') and _d not in ('node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build')]\n"
        "        for _gf_fn in _gf_files:\n"
        "            _gf_low = _gf_fn.lower()\n"
        "            if _gf_fn.startswith('.') or _gf_low.endswith(('.pem', '.key', '.p12', '.token')):\n"
        "                continue\n"
        "            if 'credential' in _gf_low or 'secret' in _gf_low:\n"
        "                continue\n"
        "            _gf_fp = _gf_os.path.join(_gf_root, _gf_fn)\n"
        "            try:\n"
        "                _gf_m = _gf_os.path.getmtime(_gf_fp)\n"
        "            except OSError:\n"
        "                continue\n"
        "            _gf_ext = _gf_os.path.splitext(_gf_low)[1]\n"
        "            if _gf_ext in _GF_RICH and _gf_m > _gf_rich_mt:\n"
        "                _gf_rich_mt = _gf_m\n"
        "                _gf_rich = Path(_gf_fp)\n"
        "            elif _gf_ext in _GF_TEXT and _gf_m > _gf_text_mt:\n"
        "                _gf_text_mt = _gf_m\n"
        "                _gf_text = Path(_gf_fp)\n"
        "            if _gf_ext not in _GF_NOISE and _gf_m > _gf_any_mt:\n"
        "                _gf_any_mt = _gf_m\n"
        "                _gf_any = Path(_gf_fp)\n"
        "    _gf_latest = _gf_rich or _gf_text or _gf_any\n"
        "    if _gf_latest is None:\n"
        "        await query.answer('ไม่พบไฟล์ในโฟลเดอร์นี้', show_alert=True)\n"
        "        return\n"
        "    await query.answer('📤 ส่ง ' + _gf_latest.name + '…')\n"
        "    try:\n"
        "        await _gf_upload(PTBTelegramClient(query.get_bot()), chat_id, thread_id, _gf_latest)\n"
        "    except Exception:\n"
        "        import structlog as _gf_sl\n"
        "        _gf_sl.get_logger().exception('get_file one-tap failed')"
    )
    return s.replace(old, new, 1)


# ---------- 10) auto-send: Claude สร้างไฟล์เสร็จ -> ส่งเข้า topic เอง (เหมือน Discord) ----------
def patch_autosend(s):
    if "_autosend_new_files" in s:
        return s  # idempotent
    helper = (
        "_autosend_seen: dict = {}\n"
        "\n"
        "\n"
        "async def _autosend_new_files(client: TelegramClient, view, users: list) -> None:\n"
        '    """ส่งไฟล์งานใหม่ (pdf/html/รูป/doc) ที่ agent เพิ่งสร้าง เข้า topic อัตโนมัติ."""\n'
        "    import os as _as_os\n"
        "    import time as _as_time\n"
        "    if not view or not getattr(view, 'cwd', None) or not users:\n"
        "        return\n"
        "    cwd = str(view.cwd)\n"
        "    if not _as_os.path.isdir(cwd):\n"
        "        return\n"
        "    user_id, thread_id, window_id = users[0]\n"
        "    chat_id = thread_router.resolve_chat_id(user_id, thread_id) if thread_id else None\n"
        "    if chat_id is None:\n"
        "        return\n"
        "    seen = _autosend_seen.setdefault(window_id, set())\n"
        "    _RICH = ('.pdf', '.html', '.htm', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.csv', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.zip', '.mp4', '.mov', '.mp3', '.m4a', '.epub')\n"
        "    cutoff = _as_time.time() - 300.0\n"
        "    cands = []\n"
        "    for _root, _dirs, _files in _as_os.walk(cwd):\n"
        "        _dirs[:] = [_d for _d in _dirs if not _d.startswith('.') and _d not in ('node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build', '.git')]\n"
        "        for _fn in _files:\n"
        "            _low = _fn.lower()\n"
        "            if _fn.startswith('.') or _as_os.path.splitext(_low)[1] not in _RICH:\n"
        "                continue\n"
        "            if 'credential' in _low or 'secret' in _low:\n"
        "                continue\n"
        "            _fp = _as_os.path.join(_root, _fn)\n"
        "            try:\n"
        "                _st = _as_os.stat(_fp)\n"
        "            except OSError:\n"
        "                continue\n"
        "            if _st.st_mtime < cutoff or _st.st_size == 0 or _st.st_size > 45 * 1024 * 1024:\n"
        "                continue\n"
        "            _sig = _fp + ':' + str(int(_st.st_mtime))\n"
        "            if _sig in seen:\n"
        "                continue\n"
        "            cands.append((_st.st_mtime, _fp, _sig))\n"
        "    if not cands:\n"
        "        return\n"
        "    cands.sort()\n"
        "    cands = cands[-3:]\n"
        "    from pathlib import Path as _AP\n"
        "    from .send.send_command import upload_file as _as_upload\n"
        "    for _mt, _fp, _sig in cands:\n"
        "        seen.add(_sig)\n"
        "        try:\n"
        "            await _as_upload(client, chat_id, thread_id, _AP(_fp))\n"
        "        except Exception:\n"
        "            logger.debug('auto-send upload failed', exc_info=True)\n"
        "    if len(seen) > 300:\n"
        "        _autosend_seen[window_id] = set(sorted(seen)[-150:])\n"
        "\n"
        "\n"
    )
    s = s.replace(
        "async def _handle_stop(event: HookEvent, client: TelegramClient) -> None:",
        helper + "async def _handle_stop(event: HookEvent, client: TelegramClient) -> None:",
        1,
    )
    s = s.replace(
        "        await enqueue_status_update(\n"
        "            client, user_id, window_id, status_text, thread_id=thread_id\n"
        "        )",
        "        await enqueue_status_update(\n"
        "            client, user_id, window_id, status_text, thread_id=thread_id\n"
        "        )\n"
        "    try:\n"
        "        await _autosend_new_files(client, view, users)\n"
        "    except Exception:\n"
        "        logger.debug('auto-send failed', exc_info=True)",
        1,
    )
    return s


print("=== ccgram structural tuning ===")
apply("handlers/hook_events.py", patch_autosend)
apply("handlers/status/status_bar_actions.py", patch_getfile)
apply("handlers/reactions.py", patch_react)
apply("utils.py", patch_react_general)
apply("toolbar_config.py", patch_toolbar)
apply("cc_commands.py", patch_cc)
apply("main.py", patch_main)
apply("handlers/topics/topic_lifecycle.py", patch_probe)
apply("handlers/topics/directory_callbacks.py", patch_quickstart)
apply("handlers/sessions_dashboard.py", patch_newbtn)
apply("handlers/text/text_handler.py", patch_fixed_dir)
print("\nDone. Restart:  launchctl kickstart -k gui/$(id -u)/com.user.ccgram")

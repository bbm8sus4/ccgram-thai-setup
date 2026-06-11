#!/usr/bin/env python3
"""Re-runnable Thai localisation patch for ccgram's main-flow UI strings.

ทำไมต้องมีไฟล์นี้: ccgram เป็น 3rd-party package, ข้อความ UI hardcode เป็นอังกฤษ.
สคริปต์นี้แทนที่เฉพาะ "ข้อความที่ผู้ใช้เห็น" (ปุ่ม/ข้อความตอบ) ด้วยภาษาไทย
โดยไม่แตะ callback_data / identifier / ชื่อไฟล์ตรวจ project / docstring สำคัญ.

รันซ้ำได้ (idempotent) — หลัง `uv tool upgrade ccgram` ให้รันไฟล์นี้อีกครั้ง:
    python3 ~/.ccgram/thai-ui-patch.py

ย้อนกลับเป็นอังกฤษ: คืนไฟล์ .bak-en (มีอยู่ข้างไฟล์ที่ถูกแก้) แล้ว restart bot.
"""
import glob
import pathlib
import py_compile

# dynamic: รอด python version เปลี่ยนตอน uv tool upgrade
_cands = sorted(glob.glob(str(pathlib.Path.home() / ".local/share/uv/tools/ccgram/lib/python*/site-packages/ccgram")))
PKG = pathlib.Path(_cands[-1]) if _cands else pathlib.Path.home() / ".local/share/uv/tools/ccgram/lib/python3.14/site-packages/ccgram"

# ordered: most-specific / longest first so substrings don't collide
REPL = [
    ("Tap a folder to enter, or select current directory", "แตะโฟลเดอร์เพื่อเข้า หรือเลือกโฟลเดอร์ปัจจุบัน"),
    ("Choose how many approvals you want for this session.", "เลือกระดับการขออนุญาตของ session นี้"),
    ("These windows are running but not bound to any topic.", "หน้าต่างเหล่านี้รันอยู่ แต่ยังไม่ผูกกับหัวข้อ"),
    ("Pick one to attach it here, or start a new session.", "เลือกอันหนึ่งเพื่อผูกที่นี่ หรือเริ่ม session ใหม่"),
    ("Please use the directory browser above, or tap Cancel.", "ใช้ตัวเลือกโฟลเดอร์ด้านบน หรือกดยกเลิก"),
    ("Please use the window picker above, or tap Cancel.", "ใช้ตัวเลือกหน้าต่างด้านบน หรือกดยกเลิก"),
    ("Create a new topic to start a session.", "สร้างหัวข้อใหม่เพื่อเริ่ม session"),
    ("This will terminate the Claude Code process.", "จะหยุดโปรเซส Claude Code"),
    ("Worktree state lost. Start over with a new message.", "ข้อมูล worktree หาย เริ่มใหม่ด้วยข้อความใหม่"),
    ("Invalid branch name; try again or tap Cancel.", "ชื่อ branch ไม่ถูกต้อง ลองใหม่หรือกดยกเลิก"),
    ("Will deliver once the agent starts.", "จะส่งให้เมื่อ AI เริ่มทำงาน"),
    ("You are not authorized to use this bot.", "คุณไม่มีสิทธิ์ใช้บอทนี้"),
    ("Please use a named topic.", "กรุณาใช้ในหัวข้อที่ตั้งชื่อแล้ว"),
    ("No active sessions.", "ยังไม่มี session ที่ใช้งานอยู่"),
    ("Which agent CLI to use?", "จะใช้ AI ตัวไหน?"),
    ("Select Working Directory", "เลือกโฟลเดอร์ที่จะทำงาน"),
    ("Select Session Mode", "เลือกโหมด session"),
    ("Select Provider", "เลือก AI"),
    ("Kill session '", "ปิด session '"),
    ("Confirm kill ", "ยืนยันปิด "),
    ("Kill {display_name}", "ปิด {display_name}"),
    ("Not your session", "ไม่ใช่ session ของคุณ"),
    ("Creating worktree", "กำลังสร้าง worktree"),
    ("(No subdirectories)", "(ไม่มีโฟลเดอร์ย่อย)"),
    ("Current branch:", "branch ปัจจุบัน:"),
    ("Current:", "ตอนนี้:"),
    ("Directory:", "โฟลเดอร์:"),
    ("Provider: {provider_icon}", "AI: {provider_icon}"),
    ("*Bind to Existing Window*", "*ผูกกับหน้าต่างที่มีอยู่*"),
    ("*New Worktree*", "*Worktree ใหม่*"),
    ("New Session", "เปิด session ใหม่"),
    ("New worktree", "worktree ใหม่"),
    ("Use this", "ใช้อันนี้"),
    ("Edit name", "แก้ชื่อ"),
    ("Use current", "ใช้ branch ปัจจุบัน"),
    ("✅ Standard", "✅ ปกติ"),
    ("Refreshed", "รีเฟรชแล้ว"),
    ("Refresh", "รีเฟรช"),
    ("Killed", "ปิดแล้ว"),
    ('"Cancel"', '"ยกเลิก"'),
    ('"Select"', '"เลือก"'),
    # --- /start welcome (new_command.py) ---
    ("Each topic is a session. Create a new topic to start.",
     "แต่ละหัวข้อ (Topic) คือ session หนึ่งงาน — สร้างหัวข้อใหม่เพื่อเริ่มได้เลยครับ"),
    # --- status bubble / wait headers (full-literal anchors, no collision) ---
    ('"Waiting for input"', '"รอคำสั่งจากคุณ"'),
    ('"Plan approval needed"', '"รออนุมัติแผน"'),
    ('f"Approval needed: {tool_name}"', 'f"รออนุมัติ: {tool_name}"'),
    ('f"{total} tasks ({done} done, {open_count} open)"',
     'f"{total} งาน ({done} เสร็จ, {open_count} ค้าง)"'),
    ('f"+{hidden_count} more"', 'f"+{hidden_count} เพิ่มเติม"'),
    ('f"{label} active"', 'f"{label} กำลังทำงาน"'),
    ('f"{label} {_PANE_BLOCKED_GLYPH} blocked"', 'f"{label} {_PANE_BLOCKED_GLYPH} ติดอยู่"'),
    ('f"{label} dead"', 'f"{label} หยุดแล้ว"'),
    ('f"idle {minutes}m"', 'f"ว่าง {minutes} นาที"'),
    ('f"idle {hours}h"', 'f"ว่าง {hours} ชม."'),
    # --- sessions dashboard header ---
    ('text = "Sessions\\n\\n"', 'text = "เซสชันที่เปิดอยู่\\n\\n"'),
    # --- error / guard toasts (longest-first for 'Window not found') ---
    ("Window not found (may have been closed)", "ไม่พบหน้าต่าง (อาจถูกปิดไปแล้ว)"),
    ("Stale browser (flow reset)", "หน้าจอหมดอายุ เริ่มใหม่อีกครั้ง"),
    ("Stale browser (topic mismatch)", "หน้าจอนี้ไม่ตรงกับหัวข้อ เริ่มใหม่"),
    ("Directory list changed, please refresh", "รายการโฟลเดอร์เปลี่ยน กดรีเฟรช"),
    ("Directory no longer exists", "ไม่พบโฟลเดอร์นี้แล้ว"),
    ("Working directory not available", "ยังไม่มีโฟลเดอร์ทำงาน"),
    ("Failed to send command", "ส่งคำสั่งไม่สำเร็จ"),
    ("Directory not found", "ไม่พบโฟลเดอร์"),
    ("Favorite not found", "ไม่พบรายการโปรด"),
    ("Window not found", "ไม่พบหน้าต่าง"),
    ("Use in a topic", "ใช้ในหัวข้อ (Topic)"),
    ("Not your window", "ไม่ใช่หน้าต่างของคุณ"),
    ("Command not found", "ไม่พบคำสั่ง"),
    # --- toolbar button labels (match ', "builtin"' context to skip emoji escapes) ---
    ('"Screen", "builtin"', '"จอภาพ", "builtin"'),
    ('"Live", "builtin"', '"สด", "builtin"'),
    ('"Get File", "builtin"', '"เอาไฟล์", "builtin"'),
    ('"Last", "builtin"', '"ล่าสุด", "builtin"'),
    ('"Close", "builtin"', '"ปิดแถบ", "builtin"'),
    # --- status-bubble keyboard (hardcoded ใน status_bubble.py, มี emoji escape) ---
    ('\\U0001f4c4 Last', '\\U0001f4c4 ล่าสุด'),
    ('\\U0001f4e5 Get File', '\\U0001f4e5 เอาไฟล์'),
    # --- cancel (emoji-prefixed) + idle status ---
    ('"✕ Cancel"', '"✕ ยกเลิก"'),
    ('\\u2713 Ready', '\\u2713 พร้อม'),
]


def patch_file(path: pathlib.Path) -> int:
    original = path.read_text(encoding="utf-8")
    patched = original
    for old, new in REPL:
        patched = patched.replace(old, new)
    if patched == original:
        return 0
    n = sum(1 for old, _ in REPL if old in original)
    bak = path.with_suffix(path.suffix + ".bak-en")
    bak.write_text(original, encoding="utf-8")
    path.write_text(patched, encoding="utf-8")
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as e:
        path.write_text(original, encoding="utf-8")  # rollback
        bak.unlink(missing_ok=True)
        print(f"  !! ROLLBACK {path.name}: syntax error -> {e}")
        return -1
    return n


def main() -> None:
    files = sorted(PKG.rglob("*.py"))
    total, changed = 0, 0
    for f in files:
        if "__pycache__" in f.parts:
            continue
        n = patch_file(f)
        if n > 0:
            changed += 1
            total += n
            print(f"  ✓ {f.relative_to(PKG)}: {n} strings")
    print(f"\nDone: {changed} files patched, {total} replacements. Restart bot to apply:")
    print("  launchctl kickstart -k gui/$(id -u)/com.user.ccgram")


if __name__ == "__main__":
    main()

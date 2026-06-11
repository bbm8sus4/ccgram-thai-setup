#!/bin/zsh
# apply.sh — ติดตั้ง/อัปเดตชุดแพตช์ Thai + tuning ของ ccgram
# รันใหม่ทุกครั้งหลัง `uv tool upgrade ccgram` (vendored source ถูกทับ)
set -e
HERE="${0:A:h}"

echo "==> 1) แปล UI เป็นไทย (idempotent)"
python3 "$HERE/patches/thai-ui-patch.py"

echo "==> 2) แพตช์โครงสร้าง (trim menu / log / probe / quick-start / new-session)"
python3 "$HERE/patches/ccgram-tune.py"

echo "==> 3) helper: cmux-telegram"
mkdir -p "$HOME/.local/bin"
cp "$HERE/bin/cmux-telegram" "$HOME/.local/bin/cmux-telegram"
chmod +x "$HOME/.local/bin/cmux-telegram"

echo "==> 4) restart bot"
launchctl kickstart -k "gui/$(id -u)/com.user.ccgram" 2>/dev/null || \
  echo "    (ยังไม่มี launchd service — ดู README ขั้นตอนติดตั้งครั้งแรก)"

echo "==> เสร็จ. ตรวจ: tail -5 ~/.ccgram/ccgram.out.log ; ควรเห็น 'Registered 9 bot commands'"

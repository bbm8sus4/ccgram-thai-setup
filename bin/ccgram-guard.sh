#!/bin/zsh
# ccgram-guard — ด่านก่อนสตาร์ทบอทจริง (launchd เรียกตัวนี้แทน "ccgram run")
# ฆ่า silent revert: ตรวจ drift -> re-apply patch -> smoke-test -> แจ้งสถานะเข้า Telegram -> exec bot
# ทำตามคำแนะนำ aidebate ข้อ 2 (upgrade safety net)
emulate -L zsh
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"

PIN_VER="3.5.2"                       # known-good version (อัปเดตเมื่อตั้งใจ upgrade)
ENVF="$HOME/.ccgram/.env"
SP=$(/usr/bin/find "$HOME/.local/share/uv/tools/ccgram" -type d -name ccgram -path '*site-packages*' 2>/dev/null | head -1)
VENV_PY=$(/usr/bin/find "$HOME/.local/share/uv/tools/ccgram" -type f -name python -path '*/bin/*' 2>/dev/null | head -1)
[ -z "$VENV_PY" ] && VENV_PY=python3

TOKEN=$(grep '^TELEGRAM_BOT_TOKEN=' "$ENVF" 2>/dev/null | cut -d= -f2-)
CHAT=$(grep '^CCGRAM_GROUP_ID=' "$ENVF" 2>/dev/null | cut -d= -f2-)
tg() { [ -n "$TOKEN" ] && [ -n "$CHAT" ] && curl -s --max-time 10 \
  "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT}" --data-urlencode "text=$1" >/dev/null 2>&1 }

msg=""

# --- 1) version pin check ---
CUR_VER=$(ccgram --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
[ "$CUR_VER" != "$PIN_VER" ] && msg="${msg}⚠️ เวอร์ชันเปลี่ยน ${PIN_VER}→${CUR_VER}
"

# --- 2) drift check: markers ของ patch ยังอยู่ไหม ---
need=0
grep -q '_probe_pin_disabled' "$SP/handlers/topics/topic_lifecycle.py" 2>/dev/null || need=1
grep -q 'CC_BUILTINS: dict\[str, str\] = {}' "$SP/cc_commands.py" 2>/dev/null || need=1
grep -q 'เซสชันที่เปิดอยู่' "$SP/handlers/sessions_dashboard.py" 2>/dev/null || need=1
grep -q '"จอภาพ"' "$SP/toolbar_config.py" 2>/dev/null || need=1

# --- 3) re-apply ถ้า drift ---
if [ "$need" = "1" ]; then
  msg="${msg}🔧 patch หลุด — re-apply อัตโนมัติ
"
  python3 "$HOME/.ccgram/thai-ui-patch.py" >/dev/null 2>&1
  python3 "$HOME/.ccgram/ccgram-tune.py"   >/dev/null 2>&1
fi

# --- 4) smoke-test ---
ok=1
grep -q '_probe_pin_disabled' "$SP/handlers/topics/topic_lifecycle.py" 2>/dev/null || ok=0
grep -q 'CC_BUILTINS: dict\[str, str\] = {}' "$SP/cc_commands.py" 2>/dev/null || ok=0
grep -q 'เซสชันที่เปิดอยู่' "$SP/handlers/sessions_dashboard.py" 2>/dev/null || ok=0
NB=$(grep -c '("start"\|("sessions"\|("resume"\|("screenshot"\|("live"\|("toolbar"\|("sync"\|("restore"\|("upgrade"' "$SP/cc_commands.py" 2>/dev/null)
"$VENV_PY" -c "import py_compile,glob;[py_compile.compile(f,doraise=True) for f in glob.glob('$SP/**/*.py',recursive=True)]" >/dev/null 2>&1 || ok=0

# --- 5) report ---
if [ "$ok" = "1" ]; then
  tg "✅ Humdum พร้อมใช้งาน (ccgram ${CUR_VER:-?}) — แพตช์ไทย+tuning ครบ, เมนู ${NB}/9
${msg}"
else
  tg "❌ Humdum: แพตช์ไม่สมบูรณ์! ตรวจด่วน (ccgram ${CUR_VER:-?})
${msg}"
fi

# --- 6) exec บอทจริง (แทนที่ process เดิม, launchd keep-alive ทำงานปกติ) ---
exec ccgram run

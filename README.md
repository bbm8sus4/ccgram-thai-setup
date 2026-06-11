# ccgram-thai-setup

ชุดแพตช์ + คอนฟิกทำให้ **[ccgram](https://github.com/alexei-led/ccgram)** (บอท Telegram ที่คุม Claude Code / Codex / Gemini / shell บน Mac จากมือถือ) **ใช้งานง่ายขึ้น เป็นภาษาไทย และไม่มีบั๊กกวนใจ** — ปรับจูนสำหรับผู้ใช้คนเดียวที่สั่งงานจากมือถือ

> ⚠️ repo นี้ไม่มีความลับใดๆ (token / user-id / group-id อยู่ใน `~/.ccgram/.env` ที่ถูก gitignore). อย่า commit `.env` จริงเด็ดขาด

---

## สิ่งที่ชุดนี้แก้ให้ (จากรีวิว 33 ปัญหา)

**ไม่มีบั๊ก / ใช้จริงไม่มีปัญหา**
- หยุด autoclose ที่ **ลบ topic ทิ้งหลังเสร็จงาน 30 นาที** (งานหาย)
- แก้บั๊ก `CCGRAM_LOG_LEVEL` ที่ถูกเมิน (log debug ตลอด) ให้ใช้ `info` จริง
- ทำ topic-existence probe ให้ **ทนต่อการไม่มีสิทธิ์ pin** (ไม่ spam error / ไม่ค้าง)

**ใช้ง่ายสุด (คงความสะดวก)**
- **Quick-start**: เปิด topic → พิมพ์ → ได้ Claude+YOLO ทันที (ข้ามขั้นเลือก AI/โหมด) — จาก 3 ขั้นเหลือ 1
- **ล็อกโฟลเดอร์**: ตั้ง `CCGRAM_QUICK_START_DIR` ให้ session ใหม่เริ่มในโฟลเดอร์เดิมเสมอ
- **toolbar กระชับ**: ตัดเหลือ 2 แถวจำเป็น (จอภาพ·สด·Esc / ↑·Enter·↓) ตัดปุ่มรกออก
- ปุ่ม **"เปิด session ใหม่"** ที่เคยกดแล้วไม่เกิดอะไร → สร้าง topic ให้จริง
- เปลี่ยน default working dir จาก `~/.ccgram` (โฟลเดอร์ลับ) → home

**ภาษาไทย / เป็นธรรมชาติ**
- แปล UI 120+ จุด (เมนู, picker, สถานะ, toast, /start) เป็นไทย
- ตัด **คำสั่งเมนู 52 → 9** (เอา 37 ตัว `↗` ที่รกออก; ยังพิมพ์ใช้ได้)
- ตั้งให้ AI (Claude/Codex/Gemini) **ตอบเป็นไทยธรรมชาติ** ไม่ใช่ภาษาแปล

---

## โครงสร้าง

```
patches/thai-ui-patch.py   แปล UI เป็นไทย (idempotent, .bak-en, py_compile+rollback)
patches/ccgram-tune.py     แพตช์โครงสร้าง 5 อย่าง (.bak-tune, py_compile+rollback)
config/.env.example        เทมเพลตคอนฟิก (ไม่มีค่าจริง)
config/com.user.ccgram.plist.example   launchd keep-alive (__HOME__ = แทนด้วย $HOME)
bin/cmux-telegram          คำสั่งสั้น `cmux-telegram` = tmux attach -t ccgram
ai-instructions/           บล็อก "ตอบไทย" สำหรับ Claude/Codex/Gemini
apply.sh                   รันแพตช์ทั้งหมด + restart (ใช้ตอนติดตั้ง/หลัง upgrade)
```

---

## ติดตั้งครั้งแรก

**1. ลง ccgram + เครื่องมือ** (Python 3.14+, tmux, claude/codex/gemini logged-in)
```bash
uv tool install ccgram
```

**2. สร้างบอท Telegram**
- @BotFather → `/newbot` → เก็บ token; `/setprivacy` → **Disable** (สำคัญ)
- เอา user-id จาก @userinfobot; สร้างกลุ่มเปิด **Topics** + เพิ่มบอทเป็น **admin** (เปิด *Manage Topics + Delete Messages + Pin Messages*); เอา group-id (`-100...`)

**3. คอนฟิก**
```bash
mkdir -p ~/.ccgram
cp config/.env.example ~/.ccgram/.env
# เติม TELEGRAM_BOT_TOKEN / ALLOWED_USERS / CCGRAM_GROUP_ID
chmod 600 ~/.ccgram/.env
```

**4. ติดตั้ง hook ของแต่ละ AI** (ให้บอทติดตามสถานะ session)
```bash
ccgram hook --install                      # claude (ใช้ ~/.claude จริง: นำหน้าด้วย CLAUDE_CONFIG_DIR=$HOME/.claude ถ้าจำเป็น)
ccgram hook --provider codex  --install
ccgram hook --provider gemini --install
```

**5. ตั้งให้ AI ตอบไทย**
```bash
cat ai-instructions/CLAUDE-language-block.md >> ~/.claude/CLAUDE.md   # ต่อท้าย อย่าทับ
cp  ai-instructions/AGENTS.md  ~/.codex/AGENTS.md
cp  ai-instructions/GEMINI.md  ~/.gemini/GEMINI.md
```

**6. keep-alive (launchd)**
```bash
sed "s#__HOME__#$HOME#g" config/com.user.ccgram.plist.example > ~/Library/LaunchAgents/com.user.ccgram.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.ccgram.plist
```

**7. แพตช์ + รัน**
```bash
./apply.sh
```

---

## วิธีใช้บนมือถือ
1. ในกลุ่ม → สร้าง **Topic ใหม่** (หรือกดปุ่ม "เปิด session ใหม่")
2. เปิด topic นั้น → พิมพ์ข้อความ → เลือกโฟลเดอร์ → **เริ่มทันที** (quick-start)
3. พิมพ์สั่งงาน (ภาษาไทยได้) · `/live` ดูจอสด · `/screenshot` · `/toolbar`
4. เข้าดูบนเครื่อง: `cmux-telegram`  (ออก: ปิดหน้าต่าง terminal)

---

## หลัง `uv tool upgrade ccgram`
vendored source ถูกทับ — รัน `./apply.sh` ใหม่ (idempotent, มี backup, py_compile+rollback)

## ความปลอดภัย
- `ALLOWED_USERS` = ด่านเดียวที่กันคนอื่นคุมเครื่อง → ใส่เฉพาะ id คุณ
- token = ความลับสูงสุด (= remote shell) เก็บ `.env` ที่ `chmod 600` อย่า commit
- YOLO/bypass = AI รันทุกอย่างไม่ถาม → เปิด 2FA บัญชี Telegram + carrier port-out PIN

---
อ้างอิง ccgram ต้นทาง: https://github.com/alexei-led/ccgram

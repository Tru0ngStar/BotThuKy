# Hướng Dẫn Chạy Bot (VPS Windows)

## Bước 1: Tạo `secrets.txt`

Trong `C:\bot`, tạo file **`secrets.txt`** (cùng cấp `main.py`):

```text
bot:7123456789:AAHxxxxxxxxxxxxxxxx
ai:AIzaSy_key_1
ai:AIzaSy_key_2
```

- **`bot:`** — token Telegram (một dòng)
- **`ai:`** — API Gemini (nhiều dòng = nhiều key, tự đổi khi lỗi 503)

Copy mẫu từ `secrets.txt.example` rồi điền key thật.

> Không đẩy `secrets.txt` lên Git.

---

## Bước 2: Chạy bot

```powershell
cd C:\bot
py -3.11 main.py
```

Bot **tự đọc** `secrets.txt` — **không** cần `$env:BOT_TOKEN=...` hay `.env`.

Thấy:

```text
[OK] Google AI: 2 API key(s), model gemini-2.5-flash
🤖 Starting bot...
✅ Bot is running!
```

Dừng: `Ctrl+C` → chạy lại `py -3.11 main.py`.

Sửa `secrets.txt` xong cũng cần restart bot.

---

## Lỗi thường gặp

| Lỗi | Cách xử lý |
|-----|------------|
| `Thiếu token Telegram` | Có dòng `bot:...` trong `C:\bot\secrets.txt` |
| `Thiếu API AI` | Có ít nhất một dòng `ai:...` |
| Chỉ `1 API key` | Thêm nhiều dòng `ai:...` (mỗi key một dòng) |
| Thiếu thư viện | `pip install -r requirements.txt` |

---

## Cấu trúc thư mục

```
C:\bot\
├── main.py
├── config.py       ← tự đọc secrets.txt
├── secrets.txt     ← token & API (bí mật)
├── handlers\
├── downloads\
└── thuky.db
```

---

## Update code trên VPS

Chỉ đè file `.py` — **giữ** `secrets.txt` và `thuky.db`.

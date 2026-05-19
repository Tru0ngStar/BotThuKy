# Hướng Dẫn Chạy Bot (VPS Windows)

## Bước 1: Tạo `secrets.txt`

Trong `C:\bot`, tạo **`secrets.txt`**:

```text
bot:7123456789:AAHxxxxxxxx
groq:gsk_xxxxxxxx
openrouter:sk-or-v1_xxxxxxxx
```

| Dòng | Ý nghĩa |
|------|---------|
| `bot:` | Token Telegram |
| `groq:` | API Groq (kênh 1 — nhanh) |
| `openrouter:` | API OpenRouter (kênh 2 — dự phòng) |

Có thể thêm nhiều dòng `groq:` / `openrouter:` — lỗi sẽ tự đổi key/kênh.

Model mặc định (sửa trong `utils/ai_client.py` nếu cần):
- Groq: `llama-3.3-70b-versatile`
- OpenRouter: `deepseek/deepseek-chat`

---

## Bước 2: Cài thư viện (một lần)

```powershell
cd C:\bot
pip install -r requirements.txt
```

---

## Bước 3: Chạy bot

```powershell
cd C:\bot
py -3.11 main.py
```

Log mong đợi:

```text
[OK] AI: Groq (1 key, llama-3.3-70b-versatile) → OpenRouter (1 key, deepseek/deepseek-chat)
🤖 Starting bot...
✅ Bot is running!
```

Không cần nhập token thủ công — bot đọc `secrets.txt`.

---

## Lỗi thường gặp

| Lỗi | Cách xử lý |
|-----|------------|
| `Thiếu token Telegram` | Dòng `bot:...` trong secrets.txt |
| `Thiếu API AI` | Ít nhất một dòng `groq:` hoặc `openrouter:` |
| `pip install openai` | Chạy trong môi trường Python đang dùng |
| Groq lỗi → OpenRouter | Tự động; kiểm tra key OpenRouter |

---

## Cấu trúc thư mục

```
C:\bot\
├── main.py
├── secrets.txt
├── utils\ai_client.py
├── handlers\
└── thuky.db
```

Update code: giữ `secrets.txt` và `thuky.db`.

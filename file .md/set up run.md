# Hướng Dẫn Chạy Telegram Bot (VPS Windows)

## Yêu Cầu

- Windows Server / Windows 10–11
- Python 3.11 (`py -3.11`)
- Bot đặt tại `C:\bot`
- Thư mục `C:\bot\.venv` đã cài sẵn thư viện (AI, telegram-bot, …)

---

## Chạy Bot (PowerShell)

Mở **PowerShell**, chạy lần lượt:

```powershell
cd C:\bot
.\.venv\Scripts\Activate.ps1
```

> Trên VPS hiện tại, `.venv` đã có đủ thư viện AI — không cần `pip install` lại trừ khi đổi máy hoặc thêm package.

Đặt token (thay `???` bằng giá trị thật):

```powershell
$env:BOT_TOKEN="???"
$env:GEMINI_API_KEY="???"
```

Chạy bot:

```powershell
py -3.11 main.py
```

Thấy `✅ Bot is running!` là bot đã lên. **Giữ cửa sổ PowerShell mở** — đóng cửa sổ = bot tắt.

---

## Cách Khác: File `.env`

Thay vì gõ biến môi trường mỗi lần, tạo `C:\bot\.env`:

```env
BOT_TOKEN=your_bot_token_here
GEMINI_API_KEY=your_gemini_key_here
```

Sau đó chỉ cần:

```powershell
cd C:\bot
.\.venv\Scripts\Activate.ps1
py -3.11 main.py
```

> Không commit file `.env` lên Git (đã có trong `.gitignore`).

---

## Xem Log

Log in ra **cùng cửa sổ PowerShell** (lỗi DB, AI, khởi động…). Không có file `log.txt` tự động trừ khi bạn tự redirect output.

---

## Cấu Trúc Thư Mục (tham khảo)

```
C:\bot\
├── main.py              ← Entry point
├── config.py
├── handlers\
├── .venv\               ← Virtualenv (đã có thư viện trên VPS)
├── .env                 ← Token (tùy chọn)
├── downloads\           ← Video / MP3 tải về
└── cookies.txt          ← Cookie TikTok (nếu cần)
```

---

## Lưu Ý

- Sửa code xong: `Ctrl+C` dừng bot, chạy lại `py -3.11 main.py`.
- Thiếu token → lỗi ngay khi import `config.py`.
- Cần FFmpeg cho `/mp3` (cài riêng trên hệ thống, không nằm trong venv).

# Hướng Dẫn Chạy Telegram Bot Tự Động Trên Windows

## Yêu Cầu

- Windows 10/11 hoặc Windows Server
- Python đã cài đặt và thêm vào PATH
- File bot đặt tại `C:\bot\ver_new.py`

---

## Bước 1: Tạo File run.bat

Mở **Notepad**, dán nội dung sau:

```bat
@echo off
cd C:\bot
python ver_new.py >> C:\bot\log.txt 2>&1
```

Lưu file:
- Vào **File → Save As**
- **Save as type:** `All Files`
- **File name:** `run.bat`
- **Location:** `C:\bot\`

> ⚠️ Đảm bảo tên file là `run.bat`, không phải `run.bat.txt`

---

## Bước 2: Mở Task Scheduler

Nhấn `Windows + R` → gõ lệnh sau → nhấn Enter:

```
taskschd.msc
```

---

## Bước 3: Tạo Task Mới

1. Ở cột bên phải, click **"Create Basic Task..."**
2. **Name:** `Telegram Bot` → click **Next**
3. **Trigger:** chọn `When the computer starts` → **Next**
4. **Action:** chọn `Start a program` → **Next**
5. Điền thông tin:
   - **Program/script:** `C:\bot\run.bat`
   - **Start in:** `C:\bot`
6. Click **Next** → **Finish**

---

## Bước 4: Cấu Hình Nâng Cao

Sau khi tạo xong, **chuột phải vào task** → chọn **Properties**

### Tab General
| Tùy chọn | Giá trị |
|---|---|
| Run whether user is logged on or not | ✅ Tick |
| Run with highest privileges | ✅ Tick |

### Tab Settings
| Tùy chọn | Giá trị |
|---|---|
| If the task fails, restart every | `1 minute` |
| Attempt to restart up to | `999 times` |
| Stop the task if it runs longer than | ❌ Bỏ tick |

Nhấn **OK** → nhập mật khẩu Windows nếu được yêu cầu.

---

## Bước 5: Kiểm Tra

Chuột phải vào task → click **Run** → mở Telegram kiểm tra bot có phản hồi không.

---

## Xem Log Khi Bot Bị Lỗi

Log được lưu tự động tại `C:\bot\log.txt`

Mở log bằng CMD:

```cmd
type C:\bot\log.txt
```

Hoặc xem log realtime:

```powershell
Get-Content C:\bot\log.txt -Wait
```

---

## Các Lệnh Quản Lý Task (CMD chạy với quyền Admin)

```cmd
# Chạy task ngay lập tức
schtasks /run /tn "Telegram Bot"

# Dừng task
schtasks /end /tn "Telegram Bot"

# Xóa task
schtasks /delete /tn "Telegram Bot" /f

# Kiểm tra trạng thái
schtasks /query /tn "Telegram Bot"
```

---

## Cấu Trúc Thư Mục

```
C:\bot\
├── ver_new.py       ← File bot chính
├── run.bat          ← File khởi động
├── log.txt          ← Log tự động tạo khi chạy
├── downloads\       ← Thư mục tải video/mp3
├── quotes\          ← Thư mục lưu quote ảnh
└── cookies.txt      ← Cookie TikTok (nếu cần)
```

---

## Lưu Ý Quan Trọng

- Không đóng cửa sổ CMD nếu đang test thủ công — Task Scheduler sẽ chạy ngầm tự động
- Nếu đổi đường dẫn thư mục bot, cập nhật lại cả `run.bat` và Task Scheduler
- Mỗi lần chỉnh sửa `ver_new.py`, cần **restart task** để áp dụng thay đổi:

```cmd
schtasks /end /tn "Telegram Bot"
schtasks /run /tn "Telegram Bot"
```
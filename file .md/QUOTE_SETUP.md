# Hướng dẫn cài đặt Quote API

## Yêu cầu

Bot của bạn cần chạy quote-api service để sử dụng chức năng quote tin nhắn.

## Cài đặt Quote API

### Cách 1: Clone và chạy từ GitHub

```bash
# Clone repository
git clone https://github.com/LyoSU/quote-api.git
cd quote-api

# Cài đặt dependencies
npm install

# Cấu hình (tùy chọn - chỉnh sửa .env nếu cần)
cp .env.example .env

# Chạy service
npm start
```

Quote API sẽ chạy tại `http://localhost:3000` (mặc định)

### Cách 2: Sử dụng Docker

```bash
# Clone repository
git clone https://github.com/LyoSU/quote-api.git
cd quote-api

# Chạy với Docker
docker compose up -d
```

## Cấu hình Bot

Bot sẽ tự động sử dụng `http://localhost:3000` làm URL của quote-api.

Nếu bạn chạy quote-api ở nơi khác, hãy set biến môi trường:

```bash
# Windows PowerShell
$env:QUOTE_API_URI = "http://your-api-url:3000"

# Linux/Mac
export QUOTE_API_URI="http://your-api-url:3000"
```

Hoặc chỉnh sửa trong file `ver new.py`:

```python
QUOTE_API_URI = os.getenv('QUOTE_API_URI', 'http://your-api-url:3000')
```

## Sử dụng

1. Reply một tin nhắn
2. Gửi lệnh `/q` để tạo quote sticker
3. Các tùy chọn:
   - `/q p` - Tạo quote dạng PNG
   - `/q i` - Tạo quote dạng file ảnh
   - `/q <số>` - Quote nhiều tin nhắn (ví dụ: `/q 3`)

## Lưu ý

- Quote API cần chạy trước khi bot khởi động
- Nếu quote-api không chạy, bot sẽ báo lỗi khi dùng lệnh `/q`
- Đảm bảo quote-api có thể truy cập được từ máy chạy bot


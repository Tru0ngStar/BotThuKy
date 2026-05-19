# Changelog - Các tính năng mới

## ✅ Đã thêm

### 1. Chức năng Quote Tin nhắn (`/q`)

**Mô tả:** Tạo quote sticker từ tin nhắn được reply, tương tự QuotLy Bot.

**Cách dùng:**
- `/q` - Quote tin nhắn được reply thành sticker
- `/q p` - Quote dạng PNG
- `/q i` - Quote dạng file ảnh
- `/q <số>` - Quote nhiều tin nhắn

**Yêu cầu:**
- Cần chạy quote-api service (xem `QUOTE_SETUP.md`)
- Quote API URL mặc định: `http://localhost:3000`
- Có thể cấu hình qua biến môi trường `QUOTE_API_URI`

**Files thay đổi:**
- Thêm hàm `quote_message()` trong `ver new.py`
- Thêm cấu hình `QUOTE_API_URI`
- Thêm thư mục `quotes/` để lưu file tạm

### 2. AI Phân tích Hình ảnh

**Mô tả:** Bot có thể đọc và phân tích hình ảnh sử dụng Google Gemini Vision API.

**Tính năng:**
- Phân tích nội dung hình ảnh
- Giải bài tập từ hình ảnh
- Đọc văn bản trong hình (OCR)
- Mô tả hình ảnh chi tiết
- Trả lời câu hỏi về hình ảnh

**Cách dùng:**
1. Gửi hình ảnh + tag bot: `@bot giải bài này`
2. Reply bot với hình ảnh
3. Chỉ gửi hình ảnh + tag/reply bot (bot sẽ tự động phân tích)

**Yêu cầu:**
- Google Gemini API key (đã có trong code)
- Thư viện `Pillow`: `pip install Pillow`

**Files thay đổi:**
- Cập nhật hàm `get_ai_response()` để hỗ trợ hình ảnh
- Cập nhật `ai_chat_handler()` để xử lý hình ảnh
- Thêm hàm `image_ai_handler()` để xử lý tin nhắn có hình ảnh
- Thêm handler cho `filters.PHOTO` và `filters.Document.IMAGE`

## 📝 Cấu hình mới

### Biến môi trường

```bash
# Quote API URL (tùy chọn)
QUOTE_API_URI=http://localhost:3000

# Google Gemini API Key (đã có trong code)
GEMINI_API_KEY=your_api_key
```

## 🔧 Dependencies mới

```bash
# Cho quote (nếu chạy quote-api local)
# Không cần thêm dependency Python, chỉ cần chạy quote-api service

# Cho AI hình ảnh
pip install Pillow
```

## 📚 Tài liệu

- `QUOTE_SETUP.md` - Hướng dẫn cài đặt quote-api
- `IMAGE_AI_SETUP.md` - Hướng dẫn sử dụng AI phân tích hình ảnh

## 🎯 Cách test

### Test Quote:
1. Reply một tin nhắn
2. Gửi `/q`
3. Kiểm tra xem có sticker được tạo không

### Test AI Hình ảnh:
1. Gửi một hình ảnh bài tập
2. Tag bot: `@bot giải bài này`
3. Kiểm tra phản hồi của bot

## ⚠️ Lưu ý

1. **Quote API:** Cần chạy quote-api service trước khi dùng lệnh `/q`
2. **AI Hình ảnh:** Bot chỉ phân tích khi được tag hoặc reply (tránh spam)
3. **Pillow:** Cần cài đặt để xử lý hình ảnh
4. **API Limits:** Google Gemini có giới hạn request, cần lưu ý khi sử dụng nhiều

## 🐛 Troubleshooting

### Quote không hoạt động:
- Kiểm tra quote-api có đang chạy không
- Kiểm tra `QUOTE_API_URI` có đúng không
- Xem log để biết lỗi cụ thể

### AI không phân tích hình ảnh:
- Kiểm tra đã cài `Pillow` chưa: `pip install Pillow`
- Kiểm tra Google Gemini API key có hợp lệ không
- Đảm bảo đã tag/reply bot khi gửi hình ảnh


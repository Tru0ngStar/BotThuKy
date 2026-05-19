# Hướng dẫn sử dụng AI phân tích hình ảnh

## Yêu cầu

- Google Gemini API key (đã có trong code)
- Thư viện `Pillow` để xử lý hình ảnh

## Cài đặt Pillow

```bash
pip install Pillow
```

## Sử dụng

### Cách 1: Gửi hình ảnh + Tag bot

1. Gửi một hình ảnh (photo hoặc file ảnh)
2. Tag bot trong caption hoặc text kèm theo
3. Bot sẽ tự động phân tích hình ảnh

Ví dụ:
```
[Gửi hình ảnh bài tập]
@your_bot giải bài này giúp tớ
```

### Cách 2: Reply bot với hình ảnh

1. Reply một tin nhắn của bot
2. Gửi hình ảnh kèm theo câu hỏi
3. Bot sẽ phân tích và trả lời

### Cách 3: Chỉ gửi hình ảnh

1. Gửi hình ảnh và tag/reply bot
2. Bot sẽ tự động mô tả và phân tích hình ảnh

## Tính năng

- ✅ Phân tích nội dung hình ảnh
- ✅ Giải bài tập từ hình ảnh
- ✅ Đọc văn bản trong hình (OCR)
- ✅ Mô tả hình ảnh chi tiết
- ✅ Trả lời câu hỏi về hình ảnh

## Lưu ý

- Bot chỉ phân tích hình ảnh khi được tag hoặc reply
- Hỗ trợ các định dạng: JPG, PNG, GIF, WebP
- Kích thước hình ảnh lớn có thể mất thời gian xử lý
- Sử dụng Google Gemini Vision API (miễn phí với giới hạn)

## Ví dụ sử dụng

### Giải bài tập toán:
```
[Gửi hình bài tập]
@your_bot giải bài này
```

### Đọc văn bản:
```
[Gửi hình có chữ]
@your_bot đọc giúp tớ đoạn này
```

### Phân tích hình ảnh:
```
[Gửi hình bất kỳ]
@your_bot mô tả hình này
```


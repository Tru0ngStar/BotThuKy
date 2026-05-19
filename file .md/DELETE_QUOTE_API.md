# Cách xóa Quote API trên VPS Ubuntu

## 🗑️ Xóa thư mục quote-api

### Nếu đang ở trong thư mục quote-api:

```bash
# Quay về thư mục cha trước
cd ..

# Xóa thư mục
rm -rf quote-api
```

### Nếu đang ở thư mục khác:

```bash
# Xóa thư mục (điều chỉnh đường dẫn nếu cần)
rm -rf /home/ubuntu/quote-api

# Hoặc nếu ở thư mục cha của quote-api
rm -rf ./quote-api
```

## ⚠️ Lưu ý quan trọng

### Nếu Quote API đang chạy với PM2:

```bash
# 1. Dừng service trước
pm2 stop quote-api
pm2 delete quote-api

# 2. Sau đó mới xóa thư mục
rm -rf quote-api
```

### Nếu Quote API đang chạy với systemd:

```bash
# 1. Dừng và vô hiệu hóa service
sudo systemctl stop quote-api
sudo systemctl disable quote-api
sudo rm /etc/systemd/system/quote-api.service
sudo systemctl daemon-reload

# 2. Sau đó mới xóa thư mục
rm -rf quote-api
```

### Nếu đang chạy thủ công (terminal):

```bash
# 1. Tìm và kill process (nếu đang chạy)
ps aux | grep "node.*quote-api"
# Hoặc
ps aux | grep "node.*index.js"

# Kill process (thay PID bằng số process ID)
kill -9 <PID>

# Hoặc kill tất cả node processes (cẩn thận!)
pkill -f "node.*quote-api"

# 2. Sau đó xóa thư mục
rm -rf quote-api
```

## ✅ Kiểm tra đã xóa chưa

```bash
# Kiểm tra thư mục còn tồn tại không
ls -la | grep quote-api

# Hoặc
test -d quote-api && echo "Còn tồn tại" || echo "Đã xóa"
```

## 🔍 Tìm vị trí thư mục (nếu không nhớ đường dẫn)

```bash
# Tìm thư mục quote-api trên toàn hệ thống
sudo find / -name "quote-api" -type d 2>/dev/null

# Tìm trong thư mục home
find ~ -name "quote-api" -type d
```

## 📝 Lệnh đầy đủ (an toàn nhất)

```bash
# 1. Dừng tất cả services liên quan
pm2 stop quote-api 2>/dev/null
pm2 delete quote-api 2>/dev/null
sudo systemctl stop quote-api 2>/dev/null
sudo systemctl disable quote-api 2>/dev/null

# 2. Kill processes nếu còn chạy
pkill -f "quote-api" 2>/dev/null

# 3. Xóa thư mục
rm -rf quote-api

# 4. Xác nhận đã xóa
ls -la | grep quote-api || echo "✅ Đã xóa thành công"
```

## ⚡ Lệnh nhanh (nếu chắc chắn không có gì đang chạy)

```bash
cd ~
rm -rf quote-api
```


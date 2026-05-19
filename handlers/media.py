"""
handlers/media.py — Media download: /download, /mp3
"""
import os
from telegram import Update
from telegram.ext import ContextTypes
from config import DOWNLOADS_DIR


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /download <URL> - Tải video từ YT/TikTok"""
    if not context.args:
        await update.message.reply_text("❌ Gửi URL, ví dụ: /download https://www.youtube.com/watch?v=xxx")
        return

    url = context.args[0]
    chat_id = update.effective_chat.id
    loading_msg = await update.message.reply_text("⏳ Chờ tí :)")

    try:
        import yt_dlp

        is_tiktok = 'tiktok.com' in url.lower()
        is_youtube = 'youtube.com' in url.lower() or 'youtu.be' in url.lower()

        ydl_opts = {
            'outtmpl': os.path.join(DOWNLOADS_DIR, '%(id)s.%(ext)s'),
            'noplaylist': True, 'quiet': True, 'no_warnings': True, 'socket_timeout': 30,
        }

        if is_youtube:
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/best[ext=mp4][height<=480]/best[height<=480]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif is_tiktok:
            ydl_opts['format'] = 'best'
            cookies_path = 'cookies.txt'
            if os.path.exists(cookies_path):
                ydl_opts['cookiefile'] = cookies_path
        else:
            ydl_opts['format'] = 'best[ext=mp4]/best'

        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl_info:
            info = ydl_info.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)

            if duration > 600:
                await loading_msg.edit_text(f"❌ Video quá dài ({duration//60} phút)!\nGiới hạn: 10 phút")
                return

        await loading_msg.edit_text(f"⏳ Đang tải: {title[:50]}...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            video_id = info.get('id', 'video')

        files = [f for f in os.listdir(DOWNLOADS_DIR) if video_id in f]
        if not files:
            raise Exception("Không tìm thấy file đã tải!")

        file_path = os.path.join(DOWNLOADS_DIR, files[0])
        file_size = os.path.getsize(file_path) / (1024 * 1024)

        if file_size > 50:
            await loading_msg.edit_text(f"❌ File quá lớn ({file_size:.1f}MB). Giới hạn 50MB.")
            os.remove(file_path)
            return

        await loading_msg.edit_text(f"⏳ Đang gửi video ({file_size:.1f}MB)...")

        with open(file_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=chat_id, video=video_file,
                caption=f"✅ {title[:100]}\n📦 {file_size:.1f}MB",
                supports_streaming=True, width=640, height=480,
                read_timeout=60, write_timeout=60
            )

        await loading_msg.delete()

        try:
            os.remove(file_path)
        except:
            pass

    except Exception as e:
        error_msg = str(e)
        if "Video unavailable" in error_msg:
            error_msg = "Video không khả dụng hoặc đã bị xóa"
        elif "Private video" in error_msg:
            error_msg = "Video ở chế độ riêng tư"
        elif "HTTP Error 429" in error_msg:
            error_msg = "YouTube giới hạn tải quá nhiều. Thử lại sau 5 phút"

        await loading_msg.edit_text(
            f"❌ Lỗi: {error_msg[:150]}\n\n💡 Thử:\n- Update: pip install -U yt-dlp\n- Video ngắn hơn (<10 phút)\n- Link khác"
        )


async def download_mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /mp3 <URL> - Tải nhạc MP3 từ YouTube/TikTok/SoundCloud"""
    user_message_id = update.message.message_id

    if not context.args:
        await update.message.reply_text("❌ Gửi URL cơ mà bé ơi")
        return

    url = context.args[0]
    chat_id = update.effective_chat.id
    loading_msg = await update.message.reply_text("🎵 Đang tải nhạc...")

    try:
        import yt_dlp

        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl_info:
            info = ydl_info.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            artist = info.get('artist', info.get('uploader', 'Unknown'))

            if duration > 900:
                await loading_msg.edit_text(f"❌ Nhạc quá dài ({duration//60} phút)!\nGiới hạn: 15 phút")
                return

        await loading_msg.edit_text(f"🎵 Đang tải: {title[:50]}...")

        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOADS_DIR, '%(id)s.%(ext)s'),
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'postprocessor_args': ['-ar', '44100'],
            'noplaylist': True, 'quiet': True, 'no_warnings': True, 'socket_timeout': 30,
        }

        cookies_path = 'cookies.txt'
        if os.path.exists(cookies_path) and 'tiktok.com' in url.lower():
            ydl_opts['cookiefile'] = cookies_path

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            video_id = info.get('id', 'audio')

        files = [f for f in os.listdir(DOWNLOADS_DIR) if video_id in f and f.endswith('.mp3')]
        if not files:
            raise Exception("Không tìm thấy file MP3!")

        file_path = os.path.join(DOWNLOADS_DIR, files[0])
        file_size = os.path.getsize(file_path) / (1024 * 1024)

        if file_size > 50:
            await loading_msg.edit_text(f"❌ File quá lớn ({file_size:.1f}MB). Giới hạn 50MB.")
            os.remove(file_path)
            return

        await loading_msg.edit_text(f"⏳ Đang gửi ({file_size:.1f}MB)...")

        with open(file_path, 'rb') as audio_file:
            await context.bot.send_audio(
                chat_id=chat_id, audio=audio_file,
                title=title, performer=artist,
                caption=f"🎵 {title}\n👤 {artist}\n📦 {file_size:.1f}MB",
                duration=int(duration) if duration else None,
                read_timeout=60, write_timeout=60
            )

        await loading_msg.delete()

        try:
            os.remove(file_path)
        except:
            pass

        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=user_message_id)
        except:
            pass

    except Exception as e:
        error_msg = str(e)
        if "Video unavailable" in error_msg:
            error_msg = "Nhạc không khả dụng hoặc đã bị xóa"
        elif "Private" in error_msg:
            error_msg = "Nhạc ở chế độ riêng tư"
        elif "HTTP Error 429" in error_msg:
            error_msg = "Quá nhiều request. Thử lại sau 5 phút"
        elif "ffmpeg" in error_msg.lower():
            error_msg = "Lỗi FFmpeg. Chạy: sudo apt install ffmpeg -y"

        await loading_msg.edit_text(
            f"❌ Lỗi: {error_msg[:150]}\n\n💡 Hỗ trợ:\n- YouTube, SoundCloud, TikTok\n- Nhạc < 15 phút\n- Cần FFmpeg"
        )

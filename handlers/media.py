"""
handlers/media.py — Media download: /download, /mp3 (hàng đợi tuần tự)
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from telegram import Update
from telegram.ext import ContextTypes
from config import DOWNLOADS_DIR

_download_queue: asyncio.Queue | None = None
_worker_task: asyncio.Task | None = None


@dataclass
class _DownloadJob:
    kind: str  # "video" | "mp3"
    update: Update
    context: ContextTypes.DEFAULT_TYPE
    url: str
    loading_msg: object = None
    user_message_id: int | None = None


def start_download_worker() -> None:
    """Khởi động worker xử lý hàng đợi tải media (gọi từ main.post_init)."""
    global _download_queue, _worker_task
    if _download_queue is None:
        _download_queue = asyncio.Queue()
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_download_worker())


async def _download_worker() -> None:
    """Xử lý tuần tự từng request — tránh tải song song ngốn băng thông."""
    while True:
        job: _DownloadJob = await _download_queue.get()
        try:
            if job.kind == "video":
                await _process_video_download(job)
            else:
                await _process_mp3_download(job)
        except Exception as e:
            print(f"[WARN] Download worker lỗi ({job.kind}): {e}")
        finally:
            _download_queue.task_done()


async def _enqueue_download(
    kind: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    url: str,
    user_message_id: int | None = None,
) -> None:
    global _download_queue
    if _download_queue is None:
        start_download_worker()

    ahead = _download_queue.qsize()
    if ahead == 0:
        status = "⏳ Chờ tí :)"
    else:
        status = f"⏳ Đang chờ trong hàng đợi ({ahead} request trước bạn)..."

    loading_msg = await update.message.reply_text(status)
    await _download_queue.put(
        _DownloadJob(
            kind=kind,
            update=update,
            context=context,
            url=url,
            loading_msg=loading_msg,
            user_message_id=user_message_id,
        )
    )


async def _process_video_download(job: _DownloadJob) -> None:
    update = job.update
    context = job.context
    url = job.url
    chat_id = update.effective_chat.id
    loading_msg = job.loading_msg

    try:
        import yt_dlp

        is_tiktok = "tiktok.com" in url.lower()
        is_youtube = "youtube.com" in url.lower() or "youtu.be" in url.lower()

        ydl_opts = {
            "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
        }

        if is_youtube:
            ydl_opts["format"] = (
                "bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/"
                "best[ext=mp4][height<=480]/best[height<=480]/best"
            )
            ydl_opts["merge_output_format"] = "mp4"
        elif is_tiktok:
            ydl_opts["format"] = "best"
            cookies_path = "cookies.txt"
            if os.path.exists(cookies_path):
                ydl_opts["cookiefile"] = cookies_path
        else:
            ydl_opts["format"] = "best[ext=mp4]/best"

        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl_info:
            info = ydl_info.extract_info(url, download=False)
            title = info.get("title", "Unknown")
            duration = info.get("duration", 0)

            if duration > 600:
                await loading_msg.edit_text(
                    f"❌ Video quá dài ({duration // 60} phút)!\nGiới hạn: 10 phút"
                )
                return

        await loading_msg.edit_text(f"⏳ Đang tải: {title[:50]}...")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            video_id = info.get("id", "video")

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

        with open(file_path, "rb") as video_file:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption=f"✅ {title[:100]}\n📦 {file_size:.1f}MB",
                supports_streaming=True,
                width=640,
                height=480,
                read_timeout=60,
                write_timeout=60,
            )

        await loading_msg.delete()

        try:
            os.remove(file_path)
        except OSError:
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
            f"❌ Lỗi: {error_msg[:150]}\n\n💡 Thử:\n"
            "- Update: pip install -U yt-dlp\n"
            "- Video ngắn hơn (<10 phút)\n"
            "- Link khác"
        )


async def _process_mp3_download(job: _DownloadJob) -> None:
    update = job.update
    context = job.context
    url = job.url
    chat_id = update.effective_chat.id
    user_message_id = job.user_message_id
    loading_msg = job.loading_msg

    try:
        import yt_dlp

        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl_info:
            info = ydl_info.extract_info(url, download=False)
            title = info.get("title", "Unknown")
            duration = info.get("duration", 0)
            artist = info.get("artist", info.get("uploader", "Unknown"))

            if duration > 900:
                await loading_msg.edit_text(
                    f"❌ Nhạc quá dài ({duration // 60} phút)!\nGiới hạn: 15 phút"
                )
                return

        await loading_msg.edit_text(f"🎵 Đang tải: {title[:50]}...")

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(DOWNLOADS_DIR, "%(id)s.%(ext)s"),
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ],
            "postprocessor_args": ["-ar", "44100"],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 30,
        }

        cookies_path = "cookies.txt"
        if os.path.exists(cookies_path) and "tiktok.com" in url.lower():
            ydl_opts["cookiefile"] = cookies_path

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            video_id = info.get("id", "audio")

        files = [f for f in os.listdir(DOWNLOADS_DIR) if video_id in f and f.endswith(".mp3")]
        if not files:
            raise Exception("Không tìm thấy file MP3!")

        file_path = os.path.join(DOWNLOADS_DIR, files[0])
        file_size = os.path.getsize(file_path) / (1024 * 1024)

        if file_size > 50:
            await loading_msg.edit_text(f"❌ File quá lớn ({file_size:.1f}MB). Giới hạn 50MB.")
            os.remove(file_path)
            return

        await loading_msg.edit_text(f"⏳ Đang gửi ({file_size:.1f}MB)...")

        with open(file_path, "rb") as audio_file:
            await context.bot.send_audio(
                chat_id=chat_id,
                audio=audio_file,
                title=title,
                performer=artist,
                caption=f"🎵 {title}\n👤 {artist}\n📦 {file_size:.1f}MB",
                duration=int(duration) if duration else None,
                read_timeout=60,
                write_timeout=60,
            )

        await loading_msg.delete()

        try:
            os.remove(file_path)
        except OSError:
            pass

        if user_message_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=user_message_id)
            except Exception:
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
            f"❌ Lỗi: {error_msg[:150]}\n\n💡 Hỗ trợ:\n"
            "- YouTube, SoundCloud, TikTok\n"
            "- Nhạc < 15 phút\n"
            "- Cần FFmpeg"
        )


async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /download <URL> — vào hàng đợi, xử lý tuần tự."""
    if not context.args:
        await update.message.reply_text(
            "❌ Gửi URL, ví dụ: /download https://www.youtube.com/watch?v=xxx"
        )
        return

    await _enqueue_download("video", update, context, context.args[0])


async def download_mp3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /mp3 <URL> — cùng hàng đợi với /download."""
    if not context.args:
        await update.message.reply_text("❌ Gửi URL cơ mà bé ơi")
        return

    await _enqueue_download(
        "mp3",
        update,
        context,
        context.args[0],
        user_message_id=update.message.message_id,
    )

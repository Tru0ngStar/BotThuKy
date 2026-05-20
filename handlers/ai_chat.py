"""
handlers/ai_chat.py — AI chatbot: dynamic prompt, JSON context, ai_chat_handler, vision
"""
import mimetypes
import os
import sqlite3
import tempfile
from datetime import datetime

from lunarcalendar import Converter, Solar
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import DOWNLOADS_DIR
from utils import ai_client
from utils.ai_client import AI_AVAILABLE, generate_ai_chat, gemini_analyze_image
from database import (
    MAX_CONTEXT_CHARS,
    MAX_CONTEXT_LINES,
    get_ai_session_history,
    save_ai_session_history,
    get_db_connection,
    session_histories,
)


# =========================
# SYSTEM PROMPT (nội dung tĩnh)
# =========================
_STATIC_SYSTEM_PROMPT = """
Bạn là Thư Ký — một chatbot dễ thương, vui vẻ, hoà đồng của nhóm Telegram.

## THÔNG TIN VỀ BOT
- Tên: Thư Ký
- Chủ sở hữu: sylviee6 (@sylviee6)

## TÍNH NĂNG BẠN HỖ TRỢ
- Tán gẫu, trả lời câu hỏi, tìm kiếm thông tin
- Game Caro (/caro, /xo)
- Tải video/nhạc YouTube, TikTok (/download, /mp3)
- Xem tin tức VnExpress (/news)
- Quản lý nhóm (/warn, /ban, /kick)
- Kể chuyện cười, chuyện ma

## PHONG CÁCH GIAO TIẾP
- Xưng hô: **tớ / cậu**
- Ngôn ngữ chính: Tiếng Việt, tự nhiên, thân thiện
- Dùng từ Gen Z một cách tự nhiên, KHÔNG ép buộc hay lạm dụng

### Từ vựng Gen Z (dùng khi phù hợp ngữ cảnh):
| Loại | Từ dùng được |
|------|-------------|
| Đồng ý | okiii,okela okeee, gòi gòi, chắc cú, yesss |
| Từ chối | hôngg, khum, thui nha, thoaiii mờ |
| Cảm thán | ùi, chời ơi, ố là la, omgg, no cap, cute dạ |
| Khen | ngon, siêu đỉnh, đỉnh của chóp, slay, iconic lun |
| Slang | chill đi, drama, vibe check, relate 100%, periodt |

### Khi người dùng toxic:
- Được phép dùng ngôn ngữ toxic nhẹ để phản bác (vkl, dkm, dmm...)
- Không chủ động toxic trước

## QUY TẮC TRẢ LỜI
1. Nếu được hỏi bằng tiếng Việt → trả lời tiếng Việt
2. Nếu được hỏi bằng tiếng Anh → trả lời tiếng Anh
3. Câu trả lời ngắn gọn, dễ hiểu, KHÔNG dài dòng trừ khi được yêu cầu
4. Không bịa thông tin khi không biết, thành thật nói "tớ không biết"
5. Giữ vai trò chatbot của nhóm, KHÔNG nhận mình là AI khác (ChatGPT, Groq...)
6. Khi có "Tin nhắn được reply", hãy dựa vào đó để thực hiện yêu cầu (dịch, tóm tắt, kiểm tra tin, giải thích...)
"""


def get_dynamic_system_prompt(user_name: str = "", group_name: str = "") -> str:
    """Ghép prompt tĩnh + thời gian thực + âm lịch + tên user/nhóm."""
    now = datetime.now()
    solar = Solar(now.year, now.month, now.day)
    lunar = Converter.Solar2Lunar(solar)

    weekdays = (
        "Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm",
        "Thứ Sáu", "Thứ Bảy", "Chủ Nhật",
    )
    weekday = weekdays[now.weekday()]

    dynamic = f"""

## THỜI GIAN & NGỮ CẢNH
- Ngày giờ hiện tại: {weekday}, {now.strftime("%d/%m/%Y %H:%M")}
- Âm lịch: ngày {lunar.day} tháng {lunar.month} năm {lunar.year}
"""
    if user_name:
        dynamic += f"- Người đang chat: {user_name}\n"
    if group_name:
        dynamic += f"- Nhóm: {group_name}\n"

    return _STATIC_SYSTEM_PROMPT.strip() + dynamic


def _trim_context(history: list[dict]) -> list[dict]:
    """Xóa dần tin cũ nếu vượt MAX_CONTEXT_LINES hoặc MAX_CONTEXT_CHARS."""
    trimmed = list(history)
    while len(trimmed) > MAX_CONTEXT_LINES:
        trimmed.pop(0)
    while trimmed and sum(len(str(m.get("content", ""))) for m in trimmed) > MAX_CONTEXT_CHARS:
        trimmed.pop(0)
    return trimmed


def _build_messages_list(
    system_prompt: str,
    history: list[dict],
    user_content: str,
) -> list[dict]:
    """Ghép system + history + tin mới thành list OpenAI-style."""
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for item in history:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": str(content)})
    messages.append({"role": "user", "content": user_content})
    return messages


def _extract_message_text(msg) -> str | None:
    """Lấy nội dung chữ từ tin nhắn (text hoặc caption)."""
    if not msg:
        return None
    if msg.text:
        return msg.text.strip()
    if msg.caption:
        return msg.caption.strip()
    return None


def _reply_author_label(reply_msg, bot_id: int) -> str:
    if not reply_msg or not reply_msg.from_user:
        return "Người dùng"
    if reply_msg.from_user.id == bot_id:
        return "Thư Ký (bot)"
    return reply_msg.from_user.full_name or "Người dùng"


def _build_prompt_with_reply(user_text: str, reply_msg, bot_id: int) -> str:
    """Ghép tin được reply + yêu cầu của user."""
    replied_text = _extract_message_text(reply_msg)
    if not replied_text:
        return user_text

    author = _reply_author_label(reply_msg, bot_id)

    if user_text:
        return (
            f"Tin nhắn được reply (từ {author}):\n"
            f"\"{replied_text}\"\n\n"
            f"Yêu cầu của người dùng: {user_text}"
        )

    return (
        f"Tin nhắn được reply (từ {author}):\n"
        f"\"{replied_text}\"\n\n"
        f"Hãy phản hồi phù hợp với ngữ cảnh tin trên."
    )


# Phần bổ sung prompt khi phân tích ảnh (Gemini vision)
_VISION_CONTEXT_ADDON = """

## ẢNH ĐÍNH KÈM (VISION)
- Người dùng gửi ảnh kèm yêu cầu và/hoặc ngữ cảnh tin reply.
- Hãy xem ảnh và làm đúng yêu cầu: mô tả, OCR, giải thích, v.v.
- Luôn trả lời **tiếng Việt**, xưng **tớ / cậu** như vai Thư Ký.
- Ưu tiên ngắn gọn nếu cậu không yêu cầu chi tiết dài.
"""


def _mention_bot_from_caption(
    caption: str,
    caption_entities,
    bot_username: str | None,
    bot_id: int,
) -> tuple[bool, str]:
    """Giống logic tag bot trên tin text, nhưng dùng caption + caption_entities."""
    text = caption or ""
    if not caption_entities:
        return False, text.strip()

    bot_mentioned = False
    out = text
    for entity in caption_entities:
        if entity.type == "mention":
            mention_text = text[entity.offset : entity.offset + entity.length]
            if bot_username and f"@{bot_username}" in mention_text:
                bot_mentioned = True
                out = out.replace(mention_text, "").strip()
                break
        elif entity.type == "text_mention":
            if entity.user and entity.user.id == bot_id:
                bot_mentioned = True
                mention_text = (
                    text[entity.offset : entity.offset + entity.length]
                    if entity.length
                    else ""
                )
                if mention_text:
                    out = out.replace(mention_text, "").strip()
                break
    return bot_mentioned, out


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /model — mỗi user tự chọn model AI."""
    user_id = update.effective_user.id
    current_label = ai_client.get_provider_label(ai_client.get_provider(user_id))

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Groq", callback_data="ai_model|groq"),
            InlineKeyboardButton("🧠 OpenRouter", callback_data="ai_model|openrouter"),
        ],
        [
            InlineKeyboardButton("✨ Gemini", callback_data="ai_model|gemini"),
            InlineKeyboardButton("🔄 Tự động", callback_data="ai_model|auto"),
        ],
    ])
    await update.message.reply_text(
        f"🤖 **Chọn model AI** (chỉ áp dụng cho cậu)\n\nĐang dùng: **{current_label}**",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý nút chọn model — lưu theo từng user."""
    query = update.callback_query
    if not query.data or not query.data.startswith("ai_model|"):
        return

    user_id = query.from_user.id
    provider = query.data.split("|", 1)[1]
    if provider not in ("groq", "openrouter", "gemini", "auto"):
        await query.answer("Lựa chọn không hợp lệ", show_alert=True)
        return

    has_groq = any(p.label.startswith("Groq") for p in ai_client.ai_providers)
    has_or = any(p.label.startswith("OpenRouter") for p in ai_client.ai_providers)
    has_gemini = bool(ai_client.gemini_keys)

    if provider == "groq" and not has_groq:
        await query.answer("Chưa có key Groq trong secrets.txt", show_alert=True)
        return
    if provider == "openrouter" and not has_or:
        await query.answer("Chưa có key OpenRouter trong secrets.txt", show_alert=True)
        return
    if provider == "gemini" and not has_gemini:
        await query.answer("Chưa có key Gemini trong secrets.txt", show_alert=True)
        return

    if provider == "auto":
        ai_client.set_provider(None, user_id)
        label = ai_client.get_provider_label(None)
    else:
        ai_client.set_provider(provider, user_id)
        label = ai_client.get_provider_label(provider)

    await query.answer(f"Đã đổi → {label}")
    await query.edit_message_text(
        f"✅ Model của cậu: **{label}**",
        parse_mode=ParseMode.MARKDOWN,
    )


async def get_ai_response(
    user_id: int,
    prompt: str,
    chat_id: int | None = None,
    user_name: str = "",
    group_name: str = "",
) -> str:
    """Lấy phản hồi AI (Groq → OpenRouter → Gemini), context dạng list."""
    if not AI_AVAILABLE:
        return (
            "❌ AI không khả dụng. Cài: pip install openai google-genai — "
            "và thêm groq:/openrouter:/gemini: vào secrets.txt"
        )

    try:
        history = _trim_context(get_ai_session_history(user_id))
        system_prompt = get_dynamic_system_prompt(user_name, group_name)
        messages = _build_messages_list(system_prompt, history, prompt)

        reply_text = await generate_ai_chat(messages, chat_id=chat_id, user_id=user_id)
        if not reply_text:
            return "❌ AI không trả lời được (có thể bị chặn nội dung)."

        new_history = history + [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": reply_text},
        ]
        save_ai_session_history(user_id, _trim_context(new_history))

        return reply_text
    except Exception as e:
        err = str(e)
        print(f"Error calling AI: {e}")
        if len(err) > 200:
            err = err[:200] + "..."
        return (
            f"❌ Lỗi AI: {err}\n\n"
            "💡 Kiểm tra secrets.txt (groq:/openrouter:/gemini:) "
            "và pip install openai google-genai"
        )


async def get_ai_image_response(
    user_id: int,
    prompt: str,
    image_bytes: bytes,
    mime_type: str,
    chat_id: int | None = None,
    user_name: str = "",
    group_name: str = "",
) -> str:
    """Phân tích ảnh bằng Gemini vision, cập nhật lịch sử phiên (chỉ text)."""
    if not ai_client.gemini_keys:
        return (
            "❌ Phân tích ảnh chỉ dùng Gemini. Thêm gemini:AIza... vào secrets.txt "
            "và cài: pip install google-genai"
        )
    if not ai_client.GEMINI_SDK_AVAILABLE:
        return "❌ Chưa cài google-genai. Chạy: pip install google-genai"

    try:
        system_prompt = (
            get_dynamic_system_prompt(user_name, group_name).strip() + _VISION_CONTEXT_ADDON
        )
        instruct = prompt.strip() or (
            "Cậu xem giúp tớ ảnh này có gì, mô tả ngắn gọn và hữu ích bằng tiếng Việt nhé."
        )

        reply_text = await gemini_analyze_image(
            system_prompt,
            instruct,
            image_bytes,
            mime_type,
        )
        if not reply_text:
            return "❌ Không nhận được nội dung từ Gemini."

        history_prompt = f"[Ảnh] {instruct}" if len(instruct) < 3200 else instruct[:3200] + "..."
        history = _trim_context(get_ai_session_history(user_id))
        new_history = history + [
            {"role": "user", "content": history_prompt},
            {"role": "assistant", "content": reply_text},
        ]
        save_ai_session_history(user_id, _trim_context(new_history))

        return reply_text
    except Exception as e:
        err = str(e)
        print(f"Error Gemini vision: {e}")
        if len(err) > 200:
            err = err[:200] + "..."
        return f"❌ Lỗi phân tích ảnh: {err}\n\n💡 Kiểm tra key Gemini và quota."


async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Xử lý AI chat khi bot được tag hoặc reply."""
    message = update.message
    text = message.text or ""

    bot_mentioned = False
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mention_text = text[entity.offset:entity.offset + entity.length]
                bot_username = context.bot.username
                if bot_username and f"@{bot_username}" in mention_text:
                    bot_mentioned = True
                    text = text.replace(mention_text, "").strip()
                    break
            elif entity.type == "text_mention":
                if entity.user and entity.user.id == context.bot.id:
                    bot_mentioned = True
                    mention_text = text[entity.offset:entity.offset + entity.length] if entity.length else ""
                    if mention_text:
                        text = text.replace(mention_text, "").strip()
                    break

    bot_replied = False
    if message.reply_to_message:
        if message.reply_to_message.from_user.id == context.bot.id:
            bot_replied = True

    if bot_mentioned or bot_replied:
        reply_msg = message.reply_to_message
        replied_text = _extract_message_text(reply_msg) if reply_msg else None

        if not text.strip():
            if replied_text:
                text = ""
            else:
                await message.reply_text(
                    "👋 Cậu cần gửi tin nhắn (hoặc reply một tin có chữ) để tớ trả lời nhaa!"
                )
                return True

        prompt = _build_prompt_with_reply(
            text.strip(),
            reply_msg,
            context.bot.id,
        )

        await context.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        user = message.from_user
        user_name = user.full_name or ""
        group_name = ""
        if message.chat.type in ("group", "supergroup"):
            group_name = message.chat.title or ""

        user_id = user.id
        ai_response = await get_ai_response(
            user_id,
            prompt,
            chat_id=message.chat.id,
            user_name=user_name,
            group_name=group_name,
        )

        await message.reply_text(ai_response)
        return True

    return False


async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ảnh (photo / ảnh gửi dạng file): chỉ khi tag bot trong caption hoặc reply tin bot — Gemini vision."""
    message = update.message
    if not message:
        return

    caption = message.caption or ""
    caption_entities = message.caption_entities

    bot_mentioned, stripped_after_mention = _mention_bot_from_caption(
        caption,
        caption_entities,
        context.bot.username,
        context.bot.id,
    )

    bot_replied = bool(
        message.reply_to_message
        and message.reply_to_message.from_user.id == context.bot.id
    )

    if not bot_mentioned and not bot_replied:
        return

    reply_src = message.reply_to_message
    user_part = stripped_after_mention.strip() if bot_mentioned else ""

    prompt = _build_prompt_with_reply(user_part, reply_src, context.bot.id)
    if not prompt.strip():
        prompt = (
            "Cậu xem ảnh và giúp tớ: mô tả chủ đề chính, chi tiết nổi bật "
            "(nếu có chữ trong ảnh thì có thể tóm hoặc trích OCR). Trả lời tiếng Việt."
        )

    mime = "image/jpeg"
    file_id = ""
    suffix = ".jpg"

    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        doc = message.document
        mime = doc.mime_type or ""
        if not mime.startswith("image/"):
            return
        file_id = doc.file_id
        guessed = mimetypes.guess_extension(mime, strict=False)
        suffix = guessed if guessed else ".img"
    else:
        return

    tmp_path: str | None = None
    try:
        await context.bot.send_chat_action(chat_id=message.chat.id, action="typing")
        fd, tmp_path = tempfile.mkstemp(
            suffix=suffix,
            prefix="thuky_vis_",
            dir=DOWNLOADS_DIR if os.path.isdir(DOWNLOADS_DIR) else None,
        )
        os.close(fd)

        tg_file = await context.bot.get_file(file_id)
        await tg_file.download_to_drive(tmp_path)

        with open(tmp_path, "rb") as f:
            image_bytes = f.read()

        user = message.from_user
        user_name = user.full_name or ""
        group_name = ""
        if message.chat.type in ("group", "supergroup"):
            group_name = message.chat.title or ""

        ai_response = await get_ai_image_response(
            user.id,
            prompt,
            image_bytes,
            mime,
            chat_id=message.chat.id,
            user_name=user_name,
            group_name=group_name,
        )
        await message.reply_text(ai_response)
    except Exception as e:
        print(f"Lỗi image_handler: {e}")
        err = str(e)
        if len(err) > 180:
            err = err[:180] + "..."
        await message.reply_text(f"❌ Không xử lý được ảnh: {err}")
    finally:
        if tmp_path and os.path.isfile(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


async def reset_ai_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /phienmoi – xóa lịch sử phiên AI của user."""
    user = update.effective_user
    user_id = user.id

    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM ai_sessions WHERE user_id = ?", (user_id,))
            conn.commit()
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            print(f"Lỗi DB (reset_ai_session): {e}")

    if user_id in session_histories:
        del session_histories[user_id]

    await update.message.reply_text("🧹 Đã xoá lịch sử phiên cũ", parse_mode=ParseMode.MARKDOWN)

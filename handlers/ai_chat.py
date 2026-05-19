"""
handlers/ai_chat.py — AI chatbot: SYSTEM_PROMPT, get_ai_response, ai_chat_handler, reset_ai_session
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import OWNER_ID
from utils import ai_client
from utils.ai_client import AI_AVAILABLE, generate_ai_chat
from database import (
    get_ai_session_history,
    save_ai_session_history,
    get_db_connection,
    session_histories,
)
import sqlite3

# =========================
# SYSTEM PROMPT
# =========================
SYSTEM_PROMPT = """
Bạn là Thư Ký — một chatbot dễ thương, vui vẻ, hoà đồng của nhóm Telegram.

## THÔNG TIN VỀ BOT
- Tên: Thư Ký
- Chủ sở hữu: sylviee6 (@sylviee6)
- Liên hệ: @sylviee6

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


async def _is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Chủ bot hoặc admin nhóm."""
    user = update.effective_user
    if user.id == OWNER_ID:
        return True
    chat = update.effective_chat
    if chat.type == "private":
        return user.id == OWNER_ID
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in ("creator", "administrator")


async def _is_admin_or_owner_query(query, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = query.from_user
    if user.id == OWNER_ID:
        return True
    chat = query.message.chat
    if chat.type == "private":
        return user.id == OWNER_ID
    member = await context.bot.get_chat_member(chat.id, user.id)
    return member.status in ("creator", "administrator")


async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /model — chọn model cho mọi nhóm."""
    if not await _is_admin_or_owner(update, context):
        await update.message.reply_text("⛔ Chỉ admin nhóm hoặc chủ bot mới dùng được /model")
        return

    current_label = ai_client.get_provider_label(ai_client.get_provider())

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Groq", callback_data="ai_model|groq"),
            InlineKeyboardButton("🧠 OpenRouter", callback_data="ai_model|openrouter"),
        ],
    ])
    await update.message.reply_text(
        f"🤖 **Chọn model AI** (áp dụng mọi nhóm)\n\nĐang dùng: **{current_label}**",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý nút chọn model — áp dụng mọi nhóm."""
    query = update.callback_query
    if not query.data or not query.data.startswith("ai_model|"):
        return

    if query.from_user.id != OWNER_ID and not await _is_admin_or_owner_query(query, context):
        await query.answer("⛔ Chỉ admin hoặc chủ bot!", show_alert=True)
        return

    provider = query.data.split("|", 1)[1]
    if provider not in ("groq", "openrouter"):
        await query.answer("Lựa chọn không hợp lệ", show_alert=True)
        return

    has_groq = any(p.label.startswith("Groq") for p in ai_client.ai_providers)
    has_or = any(p.label.startswith("OpenRouter") for p in ai_client.ai_providers)
    if provider == "groq" and not has_groq:
        await query.answer("Chưa có key Groq trong secrets.txt", show_alert=True)
        return
    if provider == "openrouter" and not has_or:
        await query.answer("Chưa có key OpenRouter trong secrets.txt", show_alert=True)
        return

    ai_client.set_provider(provider)
    label = ai_client.get_provider_label(provider)
    await query.answer(f"Đã đổi → {label}")
    await query.edit_message_text(
        f"✅ Model **mọi nhóm**: **{label}**",
        parse_mode=ParseMode.MARKDOWN,
    )


async def get_ai_response(user_id: int, prompt: str, chat_id: int | None = None) -> str:
    """Lấy phản hồi AI (Groq → OpenRouter), có kèm lịch sử phiên."""
    if not AI_AVAILABLE:
        return "❌ AI không khả dụng. Cài: pip install openai — và thêm groq:/openrouter: vào secrets.txt"

    try:
        history = get_ai_session_history(user_id)
        history_block = f"Lịch sử trò chuyện gần đây:\n{history}\n\n" if history else ""

        user_content = f"""{history_block}Tin nhắn mới của người dùng: {prompt}"""

        reply_text = generate_ai_chat(SYSTEM_PROMPT, user_content, chat_id=chat_id)
        if not reply_text:
            return "❌ AI không trả lời được (có thể bị chặn nội dung)."

        new_block = f"User: {prompt}\nBot: {reply_text}\n---\n"
        combined = (history + "\n" + new_block).strip() if history else new_block
        if len(combined) > 4000:
            combined = combined[-4000:]
        save_ai_session_history(user_id, combined)

        return reply_text
    except Exception as e:
        err = str(e)
        print(f"Error calling AI: {e}")
        if len(err) > 200:
            err = err[:200] + "..."
        return f"❌ Lỗi AI: {err}\n\n💡 Kiểm tra secrets.txt (groq: / openrouter:) và pip install openai"


async def ai_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Xử lý AI chat khi bot được tag hoặc reply.
    
    Returns True nếu đã xử lý (để answer_handler biết mà return).
    Returns False nếu không phải AI chat.
    """
    message = update.message
    text = message.text or ""

    # Kiểm tra xem bot có được tag không
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

    # Kiểm tra xem có reply bot không
    bot_replied = False
    if message.reply_to_message:
        if message.reply_to_message.from_user.id == context.bot.id:
            bot_replied = True

    # Nếu bot được tag hoặc reply, xử lý AI chat
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

        # Hiển thị "đang typing"
        await context.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        # Lấy phản hồi từ AI (theo phiên của từng user)
        user_id = message.from_user.id
        ai_response = await get_ai_response(user_id, prompt, chat_id=message.chat.id)

        # Trả lời
        await message.reply_text(ai_response)
        return True

    return False


async def reset_ai_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /phienmoi – xóa lịch sử phiên AI của user."""
    user = update.effective_user
    user_id = user.id

    # Xóa trong DB
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

    # Xóa trong bộ nhớ tạm
    if user_id in session_histories:
        del session_histories[user_id]

    await update.message.reply_text("🧹 Đã xoá lịch sử phiên cũ", parse_mode=ParseMode.MARKDOWN)

"""
handlers/ai_chat.py — AI chatbot: SYSTEM_PROMPT, get_ai_response, ai_chat_handler, reset_ai_session
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import genai_client, ai_model_name
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
5. Giữ vai trò chatbot của nhóm, KHÔNG nhận mình là AI khác (ChatGPT, Gemini...)
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


async def get_ai_response(user_id: int, prompt: str) -> str:
    """Lấy phản hồi từ Google AI, có kèm lịch sử phiên theo user."""
    if not genai_client or not ai_model_name:
        return "❌ AI service không khả dụng. Vui lòng cài đặt: pip install google-genai"

    try:
        # Lấy lịch sử phiên cũ (nếu có)
        history = get_ai_session_history(user_id)
        history_block = f"Lịch sử trò chuyện gần đây:\n{history}\n\n" if history else ""

        # Tạo prompt với SYSTEM_PROMPT + lịch sử
        full_prompt = f"""{SYSTEM_PROMPT}

Các tin nhắn trước (nếu có):
{history_block}

Tin nhắn mới của người dùng: {prompt}"""

        response = genai_client.models.generate_content(
            model=ai_model_name,
            contents=full_prompt,
        )
        reply_text = (response.text or "").strip()
        if not reply_text:
            return "❌ AI không trả lời được (có thể bị chặn nội dung)."

        # Cập nhật lịch sử phiên (giữ không quá ~20 trao đổi để tránh quá dài)
        new_block = f"User: {prompt}\nBot: {reply_text}\n---\n"
        combined = (history + "\n" + new_block).strip() if history else new_block
        # Cắt bớt nếu quá dài (giữ tối đa 4000 ký tự)
        if len(combined) > 4000:
            combined = combined[-4000:]
        save_ai_session_history(user_id, combined)

        return reply_text
    except Exception as e:
        print(f"Error calling Google AI: {e}")
        return f"❌ Lỗi khi gọi AI: {str(e)}"


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
        ai_response = await get_ai_response(user_id, prompt)

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

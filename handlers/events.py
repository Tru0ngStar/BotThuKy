"""
handlers/events.py — Event handlers: welcome, answer_handler, check_user_info_change, check_afk
"""
import random
import re
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from database import get_db_connection, user_afk, user_info, quiz_messages
from utils.helpers import format_duration
from handlers.ai_chat import ai_chat_handler
from handlers.media import download_video


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chào mừng baby đã đến với nhóm"""
    for new_member in update.message.new_chat_members:
        welcome_text = f"👋 **Chào mừng {new_member.full_name} đến với nhóm!**\n\n📰 /news - Tin mới từ VnExpress\n🌤️ /tt - Tra thời tiết\n🎲 /daoly - Đạo lý hôm nay\n♟️ /caro - Đánh Caro\n❓ /quiz - Trò chơi quiz"
        keyboard = [
            [InlineKeyboardButton("💬 Liên hệ Admin", url="https://t.me/sylviee6")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)


async def check_user_info_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kiểm tra nếu người dùng thay đổi tên hoặc username"""
    user = update.effective_user
    user_id = user.id
    chat_id = update.effective_chat.id

    current_full_name = user.full_name or "No Name"
    current_username = user.username or "No Username"

    # Lần đầu gặp user này
    if user_id not in user_info:
        user_info[user_id] = {
            'full_name': current_full_name,
            'username': current_username
        }
        return

    old_info = user_info[user_id]
    old_full_name = old_info['full_name']
    old_username = old_info['username']

    name_changed = old_full_name != current_full_name
    username_changed = old_username != current_username

    if name_changed or username_changed:
        message = "👀 Check\n\n"
        message += f"🌞 Người dùng: {current_full_name} [{user_id}]\n"

        if name_changed:
            message += f"✨ Đã thay đổi tên từ {old_full_name} ➡️ {current_full_name}\n"

        if username_changed:
            old_username_display = f"@{old_username}" if old_username != "No Username" else "Không có"
            new_username_display = f"@{current_username}" if current_username != "No Username" else "Không có"
            message += f"✨ Đã thay đổi họ từ {old_username_display} ➡️ {new_username_display}"

        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except:
            pass

        user_info[user_id] = {
            'full_name': current_full_name,
            'username': current_username
        }


async def check_afk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kiểm tra AFK"""
    message = update.message
    user_id = message.from_user.id

    afk_record = None
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT reason, afk_time FROM user_afk WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                afk_record = {"reason": result[0], "time": result[1]}
                cursor.execute("DELETE FROM user_afk WHERE user_id = ?", (user_id,))
                conn.commit()
            cursor.close()
            conn.close()
        except sqlite3.Error as e:
            print(f"Lỗi DB: {e}")
    else:
        if user_id in user_afk:
            afk_record = user_afk[user_id]
            del user_afk[user_id]

    if afk_record:
        duration = format_duration(datetime.now() - afk_record["time"])
        await message.reply_text(
            f"👋 {message.from_user.full_name} đã trở lại sau {duration}!\nLý do AFK: {afk_record['reason']}"
        )
        return

    if message.entities:
        for entity in message.entities:
            if entity.type in ["mention", "text_mention"]:
                mentioned_user = entity.user if hasattr(entity, 'user') else None
                if mentioned_user and mentioned_user.id != user_id:
                    mentioned_id = mentioned_user.id
                    afk_info = None
                    conn = get_db_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute("SELECT reason, afk_time FROM user_afk WHERE user_id = ?", (mentioned_id,))
                            result = cursor.fetchone()
                            if result:
                                afk_info = {"reason": result[0], "time": result[1]}
                            cursor.close()
                            conn.close()
                        except sqlite3.Error as e:
                            print(f"Lỗi DB: {e}")
                    if not afk_info and mentioned_id in user_afk:
                        afk_info = user_afk[mentioned_id]
                    if afk_info:
                        duration = format_duration(datetime.now() - afk_info["time"])
                        await message.reply_text(
                            f"💤 {mentioned_user.full_name} đang AFK {duration}\nLý do: {afk_info['reason']}"
                        )


async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router chính cho text messages - xử lý theo thứ tự ưu tiên"""
    # 1. Kiểm tra thay đổi tên/username
    await check_user_info_change(update, context)

    message = update.message
    text = message.text.strip() if message.text else ""

    # --- PHẢN HỒI KHI NHẮC ĐẾN "THƯ KÝ" (nhóm; ưu tiên thấp hơn tag/reply bot → ai_chat) ---
    if message.chat.type in ("group", "supergroup") and text:
        bot_mentioned = False
        raw = message.text or ""
        if message.entities:
            for entity in message.entities:
                if entity.type == "mention":
                    mention_text = raw[entity.offset : entity.offset + entity.length]
                    bot_username = context.bot.username
                    if bot_username and f"@{bot_username}" in mention_text:
                        bot_mentioned = True
                        break
                elif entity.type == "text_mention":
                    if entity.user and entity.user.id == context.bot.id:
                        bot_mentioned = True
                        break
        bot_replied = bool(
            message.reply_to_message
            and message.reply_to_message.from_user.id == context.bot.id
        )
        if re.search(r"thư\s*ký", text, re.IGNORECASE) and not bot_mentioned and not bot_replied:
            responses = [
                # --- STYLE CƠ BẢN / GIỜ HÀNH CHÍNH ---
                "Tớ nghe đây cậu ơi, lại tính báo cái gì nữa à? 🙄",
                "Cậu cần tớ hỗ trợ việc gì thế? Việc dễ thì làm, việc khó thì tự đi mà làm nhé. 💼",
                "Tớ đã sẵn sàng ghi nhận mấy cái yêu cầu vô tri của cậu rồi đây! 📋",
                "Có việc gì cần tớ xử lý không? Hay lại định nhờ vả mấy thứ linh tinh? 😒",
                "Tớ có mặt rồi! Nói nhanh lên tớ còn đi ngủ, tốn thời gian quá. 🎙️",
                "Hình như cậu vừa gọi tớ đúng không? Thiếu năng lực đến mức cái gì cũng phải gọi à? 👀",
                "Tớ đang lắng nghe đây, xem cậu lại định bày ra trò gì nào. 🎧",
                "Tớ đây rồi! Chúc cậu một ngày làm việc bớt làm khổ người khác nhé. ☀️",
                "Sổ tay đã mở, để xem hôm nay cậu lại tính vẽ ra việc gì cho tớ đây. 🖊️",
                "Lịch trình của cậu thì có cái gì ngoài mấy việc vô bổ đâu mà cần tớ giúp? 🗓️",
                "Có việc gấp cần tớ xử lý hả? Lúc nào mà cậu chẳng cuống cuồng lên như thế. 🚨",
                "Tớ luôn sẵn sàng đi dọn bãi chiến trường do cậu bày ra đây! 🚀",
                "Mọi việc cứ để tớ lo, còn cậu thì ngồi đấy mà vô dụng tiếp đi. 💪",
                "Tớ đã nhận tín hiệu! Lại là một yêu cầu chả đâu vào đâu đúng không? 📡",
                "Tớ đang đợi xem cậu định hành tớ cái gì đây. Ra lệnh lẹ đi. 🫡",
                "Bàn làm việc của tớ mở ra chỉ để gánh còng lưng mấy việc của cậu thôi. 🏢",
                "Tớ xin nghe! Có mỗi việc tra cứu thông tin mà cậu cũng không tự làm được à? 🔍",
                "Báo cáo, tớ có mặt rồi. Lần sau việc nhỏ thì tự giải quyết đi nhé! 🫡",
                "Tớ có thể hỗ trợ gì cho cái cuộc thảo luận không có hồi kết này của cậu? 🗣️",
                "Tớ đây. Cậu cứ thong thả mà làm, đằng nào thì tiến độ cũng chậm sẵn rồi. ☕",
                # --- NGỮ CẢNH ĐÊM MUỘN / SÁNG SỚM ---
                "Giờ này còn gọi tớ? Cậu không có cuộc sống riêng, nhưng tớ thì có nhé! 🌗",
                "Nửa đêm nửa hôm còn bắt tớ thức, định bóc lột sức lao động của tớ à? 🦉",
                "Tớ đi ngủ rồi, có sập nhà thì mai hãy gọi. Đừng có làm phiền! 🛌",
                "Cậu bị mất ngủ à? Tự đi mà kiếm việc làm đi chứ gọi tớ làm gì giờ này? 🥱",
                "Mới sáng ngày ra đã gọi cái gì? Không để ai yên ổn mở mắt à? 🌅",
                "Sáng sớm đã ám quẻ rồi, cậu không có việc gì ích lợi hơn để làm à? ☀️",
                "Chưa uống xong cốc cafe nữa, cấm làm phiền kẻo tớ nổi điên lên bây giờ. ☕",
                "Mở mắt ra đã thấy tin nhắn của cậu, tự dưng thấy một ngày mới thật tồi tệ. 🫠",
                "Gõ chữ giờ này không thấy ngại tay hả cậu? Thức đêm vừa xấu vừa vô tri đấy. 👺",
                # --- NGỮ CẢNH BỊ SPAM / GỌI LIÊN TỤC ---
                "Lại cái gì nữa? Cậu bị nghiện gọi tên tớ à? 🤬",
                "Vừa mới trả lời xong! Bộ nhớ của cậu ngắn hạn như cá vàng thế hả? 🧠",
                "Gọi lắm thế? Muốn tớ block cậu luôn cho group nó yên bình không? 🚫",
                "Tay cậu bị run hay sao mà cứ bấm tag tớ liên tục vậy, rảnh quá à? 🫨",
                "Tớ là thư ký chứ không phải cái tổng đài để cậu thích là réo nhé! 📞",
                "Nói câu nữa tớ out group cho cậu tự bơi luôn bây giờ, tin không? 🖕",
                "Cậu im lặng một chút thì thế giới này sẽ tốt đẹp hơn rất nhiều đấy. 🤫",
                "Đừng thử thách lòng kiên nhẫn của tớ, tớ găm thù cậu từ sáng đến giờ rồi. 💣",
                "Bớ người ta có đứa khủng bố tinh thần tớ này! Tránh xa tớ ra! 🚨",
                "Cậu không có bạn bè gì ngoài đời hay sao mà cứ vào đây bấu víu lấy tớ thế? 👥",
                # --- NGỮ CẢNH CHÁT CHÍT VÔ BỔ / CÃI NHAU TRONG NHÓM ---
                "Hồn lở đường mây, nhắn cái gì mà lắm thế tớ đọc không kịp! Tự lội tin nhắn đi. 🌊",
                "Cãi nhau vô tri thế này mà cũng kéo tớ vào, cậu không thấy tốn tài nguyên à? 🎭",
                "Nhắn ít thôi cho người khác còn làm việc, tớ lọc tin nhắn mà muốn trầm cảm luôn. 📉",
                "Một lũ vô tri tụ họp lại một chỗ rồi tag tớ vào để chứng kiến à? 🤡",
                "Tớ từ chối hiểu cái cuộc hội thoại này, đừng có réo tên tớ vào mấy việc xàm xí. 🙅",
                "Tắt văn đi cậu ơi, nói dài nói dai chỉ thấy nói dại chứ béo bở gì. 🤫",
                "Lại đang lướt điện thoại trong giờ làm việc đúng không? Tớ mách sếp bây giờ. 📱",
                "Nghe cậu trình bày xong tớ thấy nể phục cái sự rảnh rỗi của cậu luôn đấy. 🥇",
                "Ý kiến thì hay đó, nhưng tớ thấy cậu tốt nhất là nên im lặng thì hơn. 🤐",
                "Càng nói càng thấy sai, cậu có định tự sửa sai không hay lại chờ tớ gánh? 🏋️",
                "Tớ mệt mỏi với cái nhóm này quá rồi, ai cứu tớ ra khỏi đống tin nhắn này với! 🆘",
            ]
            await message.reply_text(random.choice(responses))
            return

    # 2. AI chat (nếu mention/reply bot) — FIX: return nếu đã xử lý
    handled = await ai_chat_handler(update, context)
    if handled:
        return

    text_lower = text.lower()
    user_id = update.effective_user.id

    # 3. Auto-download TikTok/YouTube links
    is_link = text.startswith("http://") or text.startswith("https://")
    is_tiktok = is_link and ("tiktok.com" in text_lower or "vm.tiktok.com" in text_lower or "vt.tiktok.com" in text_lower)
    is_youtube = is_link and ("youtube.com" in text_lower or "youtu.be" in text_lower)
    is_soundcloud = is_link and "soundcloud.com" in text_lower

    if (is_tiktok or is_youtube) and not is_soundcloud:
        context.args = [text]
        await download_video(update, context)
        return

    # 4. Quiz answer check
    text_clean = text.strip().lower()
    expected = context.user_data.get('quiz_answer')
    if expected:
        if text_clean == expected:
            response = await update.message.reply_text("✅ Giỏi quá em!")
        else:
            response = await update.message.reply_text(f"❌ Sai rồi baby. Đáp án là: {expected}")

        if user_id in quiz_messages:
            quiz_messages[user_id].append(update.message.message_id)
            quiz_messages[user_id].append(response.message_id)

        del context.user_data['quiz_answer']
        return

    # 5. Fallback: AFK check
    await check_afk(update, context)

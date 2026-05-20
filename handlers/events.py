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

from config import OWNER_ID
from database import (
    delete_group,
    get_db_connection,
    quiz_messages,
    set_group_status,
    upsert_active_group,
    user_afk,
    user_info,
)
from utils.helpers import format_duration
from handlers.ai_chat import ai_chat_handler
from handlers.media import download_video


async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Chào mừng baby đã đến với nhóm"""
    welcome_responses = [
        # --- KIỂU PHÁN XÉT NĂNG LỰC / BÀI XÍCH ---
        "Chào mừng {name} đến với ổ vô tri này, hy vọng cậu không làm tăng độ tạ của nhóm. ☠️",
        "Lại có thành viên mới vào báo nữa rồi à? Nhóm này chưa đủ loạn hay sao. 😮‍婊",
        "Né tớ ra nhé {name}, tớ gánh mấy đứa cũ ở đây đã đủ còng lưng rồi. 🏋️",
        "Tớ nghe nói nhóm sắp đón thêm một quả tạ, hóa ra là {name} à? 🏋️‍♂️",
        "Chào mừng {name}, mong là cậu có ích hơn mấy đứa ăn hại đang ngồi sẵn trong này. 👥",
        "Lại thêm một chiếc chiếu mới xộc mùi vô tri bước vào đây. 🧊",
        "Nhóm đang thiếu người làm việc, chứ người đứng xem với báo như {name} thì thừa rồi. 🙄",
        "Nhìn Avatar là thấy một bầu trời báo thủ rồi, vào nhóm bớt bớt cái nết lại nghe chưa. 📸",
        "Chào {name}, hy vọng chỉ số IQ của cậu không thấp hơn nhiệt độ phòng điều hòa. ❄️",
        "Để tớ chống mắt lên xem {name} trụ lại cái nhóm này được bao nhiêu ngày. 👁️",
        # --- KIỂU CẢNH BÁO / ĐE DỌA CỌC CẰN ---
        "Chào {name} nhé! Vào nhóm thì nhớ tắt thông báo đi không lại trầm cảm đấy. 📉",
        "Vào nhóm rồi thì nhớ đọc ghim, đừng có mở mồm ra hỏi mấy câu ngớ ngẩn nhé. 📋",
        "Chào {name} mới vào nhé! Nhớ mang theo não trước khi phát biểu trong này nha. 🧠",
        "Chào {name}, vào đây thì tém tém cái nết lại kẻo tớ block không kịp báo trước đâu. 🚫",
        "Ủa ai mời {name} vào đây thế? Thôi lỡ vào rồi thì ngồi im đừng có làm phiền tớ. 🤫",
        "Vào thì vào nhanh lên rồi đóng cái cửa lại, gió máy quá {name} ơi. 🚪",
        "Đã vào đây thì phải ngoan, tớ gõ đầu mấy đứa cũ ở đây quen tay rồi đấy nhé. 🔨",
        "Tớ không có nghĩa vụ phải đi dọn rác do thành viên mới bày ra đâu, nhớ đấy! 🚮",
        "Biết luật nhóm chưa {name}? Chưa biết thì tự đi mà tìm hiểu, đừng có réo tớ. 😤",
        "Nói trước là tớ rất cọc, đừng có tag tớ vào mấy cái thắc mắc sơ đẳng của cậu. ⚠️",
        # --- KIỂU MỈA MAI SỰ RẢNH RỖI / VÔ TRI ---
        "Chào mừng {name}! Chúc cậu sống sót qua 24 giờ đầu tiên ở cái động này. 💀",
        "Thêm một người rảnh rỗi nữa gia nhập nhóm. Thôi thì cứ tự nhiên đi {name}. ☕",
        "Chào mừng {name} đến với nơi hội tụ của những chuyên gia nói đạo lý nhưng sống lỗi. 🤡",
        "Hy vọng {name} vào nhóm để làm việc chứ không phải để spam mấy thứ rác rưởi. 🗑️",
        "Lại một linh hồn tội nghiệp nữa sa chân vào cái hố không có lối thoát này. 🕳️",
        "Hết việc ngoài đời rồi hay sao mà lại chui vào cái nhóm này để xàm xí vậy {name}? 📱",
        "Chào mừng đến với rạp xiếc, {name} vừa được phong danh hiệu hề mới của nhóm. 🎪",
        "Nhóm này vốn đã bất ổn rồi, {name} vào nữa là thành thảm họa luôn đấy. 🌪️",
        "Nhìn {name} có vẻ rảnh, tí nữa lội hết đống tin nhắn cũ của nhóm rồi tóm tắt lại cho tớ đi. 📝",
        "Chào {name}, hi vọng cậu không phải kiểu người suốt ngày gửi link rác với sticker vô nghĩa. 🚯",
        # --- KIỂU CHÊ BAI / THÁI ĐỘ \"LỒI LÕM\" ---
        "Ủa ai đây? Ai cho người lạ vào phòng làm việc của tớ thế này? 🏢",
        "Nói thật là tớ cũng chẳng hào hứng gì khi có thêm thành viên mới đâu, nhưng thôi cứ chào cái. 😒",
        "Chào {name}, vào nhóm nhớ giữ trật tự cho tớ ngủ, cấm nháo nhào lên. 🛌",
        "Lại một người nữa vào để làm loãng cái sự tập trung vốn đã ít ỏi của nhóm này. 📉",
        "{name} mới vào đúng không? Tự giác giới thiệu bản thân ngắn gọn rồi im lặng đi nhé. 🎤",
        "Vào đây thì bớt thể hiện lại, trong này toàn cao thủ báo đời thôi {name} không lại được đâu. 🥇",
        "Chào mừng {name} đến với thế giới của những chiếc deadline mọc rêu, hi vọng cậu không nợ theo. 🍄",
        "Mới nhìn qua đã thấy không cùng tần số rồi, nhưng lỡ vào rồi thì chịu thôi. 📻",
        "Chào {name}, chúc cậu không bị bay màu khỏi nhóm sau vài câu phát biểu đầu tiên. 🧨",
        "Thêm một người, thêm một nỗi lo. Tớ lại phải quản lý thêm một đứa rồi. 😮‍💨",
        # --- KIỂU TIỄN KHÁCH SỚM / KHÔNG HOAN NGHÊNH ---
        "Nếu {name} định vào đây để thả thính hay spam bán hàng thì mời cậu tự out luôn cho nhanh. 🚪",
        "Tớ cá là {name} sẽ out nhóm trong vòng 3 nốt nhạc vì không chịu nổi nhiệt đâu. 🎵",
        "Chào {name}, nếu thấy nhóm ồn quá thì nút 'Leave Group' ở ngay góc màn hình nhé. ↖️",
        "{name} vào nhóm có mục đích gì không? Không có thì ra ngoài cho rộng chỗ. 🙅",
        "Tớ chuẩn bị sẵn nút kích rồi, {name} mà hó hé câu nào ngáo ngơ là bay màu ngay. 💣",
        "Vào nhóm chỉ để tàu ngầm xem trộm tin nhắn đúng không? Tớ ghét nhất kiểu đấy. 🕵️",
        "Chào mừng {name}, mong cậu không làm tớ phải tốn công bấm nút xóa tài khoản khỏi nhóm. 🛑",
        "Nhóm này không hoan nghênh mấy đứa lười biếng đâu, {name} tự biết mình thuộc loại nào rồi chứ? 🦥",
        "{name} mới vào à? Nhớ nộp lệ phí cho tớ... đùa đấy nhưng ngoan ngoãn thì sống lâu nhé. 💰",
        "Chào hay không chào cũng thế, đằng nào tuần sau {name} chẳng chán rồi tự out. ⏳",
    ]

    for new_member in update.message.new_chat_members:
        # Bỏ qua nếu bot tự join (đã có greet_new_group xử lý)
        if new_member.id == context.bot.id:
            continue
        name = new_member.full_name
        text = random.choice(welcome_responses).format(name=name)
        await update.message.reply_text(text)


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


def _fmt_username(username: str | None) -> str:
    if not username:
        return "(không có)"
    return f"@{username}" if not username.startswith("@") else username


async def _notify_owner_new_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    chat_title: str,
    added_by,
):
    added_by_id = getattr(added_by, "id", None)
    added_by_username = getattr(added_by, "username", None)
    added_by_full_name = getattr(added_by, "full_name", None) or "Người dùng"

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    text = (
        "🧾 **Bot được thêm vào nhóm mới**\n\n"
        f"- Nhóm: **{chat_title}**\n"
        f"- ID nhóm: `{chat_id}`\n"
        f"- Người thêm bot: **{added_by_full_name}** ({_fmt_username(added_by_username)})\n"
        f"- ID người thêm: `{added_by_id}`\n"
        f"- Thời gian: {now}\n"
    )

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Chấp nhận", callback_data=f"group_accept|{chat_id}"),
                InlineKeyboardButton("❌ Từ chối", callback_data=f"group_reject|{chat_id}"),
            ]
        ]
    )
    await context.bot.send_message(OWNER_ID, text, reply_markup=kb, parse_mode=ParseMode.MARKDOWN)


async def handle_my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    MY_CHAT_MEMBER: phát hiện bot được add / bị kick / rời nhóm.
    - Khi được add: lưu DB (pending) + báo owner kèm nút accept/reject.
    - Khi bị kick/left: set inactive.
    """
    chat_member = getattr(update, "chat_member", None)
    if not chat_member:
        return

    new = chat_member.new_chat_member
    old = chat_member.old_chat_member

    if not new or new.user.id != context.bot.id:
        return

    chat = chat_member.chat
    if chat.type not in ("group", "supergroup"):
        return

    new_status = new.status
    old_status = old.status if old else None

    became_member = new_status in ("member", "administrator")
    was_member = old_status in ("member", "administrator")

    if became_member and not was_member:
        added_by = getattr(chat_member, "from_user", None)
        upsert_active_group(
            chat_id=chat.id,
            chat_title=chat.title,
            added_by_id=getattr(added_by, "id", None),
            added_by_username=getattr(added_by, "username", None),
            status="pending",
            approved_manually=0,
        )
        try:
            await _notify_owner_new_group(update, context, chat.id, chat.title or "(không có tên)", added_by)
        except Exception as e:
            print(f"Lỗi notify_owner_new_group: {e}")
        return

    # Bot bị kick / rời nhóm
    if new_status in ("left", "kicked"):
        set_group_status(chat.id, "inactive")


async def group_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback cho owner: accept/reject/leave group."""
    query = update.callback_query
    if not query or not query.data:
        return

    if query.from_user.id != OWNER_ID:
        await query.answer("⛔ Chỉ owner dùng được.", show_alert=True)
        return

    try:
        action, chat_id_str = query.data.split("|", 1)
        chat_id = int(chat_id_str)
    except Exception:
        await query.answer("Dữ liệu không hợp lệ", show_alert=True)
        return

    if action == "group_accept":
        set_group_status(chat_id, "active")
        await query.answer("Đã chấp nhận")
        await query.edit_message_text("✅ Đã chấp nhận", parse_mode=ParseMode.MARKDOWN)
        return

    if action == "group_reject":
        try:
            await context.bot.leave_chat(chat_id)
        except Exception as e:
            print(f"Lỗi leave_chat (reject): {e}")
        set_group_status(chat_id, "inactive")
        await query.answer("Đã từ chối")
        await query.edit_message_text("❌ Đã từ chối và rời nhóm", parse_mode=ParseMode.MARKDOWN)
        return

    if action == "group_leave":
        try:
            await context.bot.leave_chat(chat_id)
        except Exception as e:
            await query.answer("Không rời được", show_alert=True)
            print(f"Lỗi leave_chat (leave): {e}")
            return
        delete_group(chat_id)
        await query.answer("Đã rời nhóm")
        await query.edit_message_text("🚪 Đã rời nhóm và xóa khỏi DB", parse_mode=ParseMode.MARKDOWN)
        return


async def greet_new_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Chào mừng khi bot Thư Ký được add vào nhóm mới (MY_CHAT_MEMBER).
    """
    chat_member = getattr(update, "chat_member", None)
    if not chat_member:
        return

    new = chat_member.new_chat_member
    old = chat_member.old_chat_member

    # Chỉ xử lý khi chính bot được thêm vào / bật lại
    if not new or new.user.id != context.bot.id:
        return

    new_status = new.status
    old_status = old.status if old else None

    became_member = new_status in ("member", "administrator")
    was_member = old_status in ("member", "administrator")
    if not became_member or was_member:
        return

    chat = chat_member.chat
    if chat.type not in ("group", "supergroup"):
        return

    greet_text = (
        "🤖 **Xin chào mọi người!**\n\n"
        "Tớ là Thư Ký — bot hỗ trợ nhóm.\n"
        "Gõ /help để xem danh sách lệnh nhé!\n\n"
        "Tớ sẽ phụ trách quán xuyến cái nhóm này, đừng có làm loạn! 😤"
    )

    try:
        await context.bot.send_message(chat.id, greet_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Lỗi greet_new_group: {e}")

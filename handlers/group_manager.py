"""
handlers/group_manager.py — Owner group management: /gr, /leave, /addgr
"""
from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import OWNER_ID
from database import (
    delete_group,
    list_groups as list_groups_db,
    set_group_status,
    upsert_active_group,
)


def _owner_only(update: Update) -> bool:
    user = update.effective_user
    return bool(user and user.id == OWNER_ID)


def _private_only(update: Update) -> bool:
    chat = update.effective_chat
    return bool(chat and chat.type == "private")


async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /gr — chỉ owner, chỉ private: xem danh sách nhóm đang active."""
    if not _owner_only(update):
        return
    if not _private_only(update):
        await update.message.reply_text("⚠️ /gr chỉ dùng trong chat riêng với owner.")
        return

    rows = list_groups_db(status="active")
    if not rows:
        await update.message.reply_text("😿 Hiện bot chưa có nhóm nào đang active trong DB.")
        return

    lines = ["📌 **Danh sách nhóm đang hoạt động:**\n"]
    keyboard = []
    for idx, (chat_id, title, added_by_id, added_by_username, added_at, status, approved_manually) in enumerate(rows, start=1):
        title_disp = title or "(không có tên)"
        tag = "👤 Thủ công" if int(approved_manually or 0) == 1 else "🤖 Auto"
        lines.append(f"{idx}. {tag} — {title_disp}\n   ID: `{chat_id}`")
        short_title = (title_disp[:20] + "…") if len(title_disp) > 20 else title_disp
        keyboard.append([InlineKeyboardButton(f"🚪 Rời: {short_title}", callback_data=f"group_leave|{chat_id}")])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def leave_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /leave {chat_id} — chỉ owner, chỉ private."""
    if not _owner_only(update):
        return
    if not _private_only(update):
        await update.message.reply_text("⚠️ /leave chỉ dùng trong chat riêng với owner.")
        return
    if not context.args:
        await update.message.reply_text("Dùng: `/leave -1001234567890`", parse_mode="Markdown")
        return
    try:
        chat_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ chat_id phải là số nguyên.")
        return

    try:
        await context.bot.leave_chat(chat_id)
    except Exception as e:
        err = str(e).lower()
        # Nhóm đã bị deactivate hoặc bot không còn trong nhóm → xóa DB thẳng
        if "deactivated" in err or "not found" in err or "kicked" in err or "chat_id_invalid" in err:
            delete_group(chat_id)
            await update.message.reply_text(
                f"⚠️ Nhóm `{chat_id}` đã deactivated (không còn thành viên nào).\n"
                f"✅ Đã xóa khỏi DB.",
                parse_mode="Markdown",
            )
            return
        await update.message.reply_text(f"❌ Không rời được nhóm: {str(e)[:200]}")
        return

    delete_group(chat_id)
    await update.message.reply_text(
        f"✅ Đã rời nhóm `{chat_id}` và xóa khỏi DB.", parse_mode="Markdown"
    )


async def add_group_manually(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /addgr {chat_id hoặc @username} — chỉ owner, chỉ private."""
    if not _owner_only(update):
        return
    if not _private_only(update):
        await update.message.reply_text("⚠️ /addgr chỉ dùng trong chat riêng với owner.")
        return
    if not context.args:
        await update.message.reply_text("Dùng: `/addgr -1001234567890` hoặc `/addgr @ten_nhom`", parse_mode="Markdown")
        return

    raw = context.args[0].strip()
    chat_id: int | None = None
    chat_obj = None

    if raw.startswith("@"):
        try:
            chat_obj = await context.bot.get_chat(raw)
            chat_id = chat_obj.id
        except Exception as e:
            await update.message.reply_text(f"❌ Không tìm thấy nhóm {raw}: {str(e)[:200]}")
            return
    else:
        try:
            chat_id = int(raw)
        except ValueError:
            await update.message.reply_text("❌ Đầu vào không hợp lệ. Dùng chat_id (số) hoặc @username_nhóm.")
            return

    try:
        if chat_obj is None:
            chat_obj = await context.bot.get_chat(chat_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Không lấy được thông tin nhóm: {str(e)[:200]}")
        return

    # Kiểm tra bot có trong nhóm chưa
    try:
        me = await context.bot.get_me()
        member = await context.bot.get_chat_member(chat_obj.id, me.id)
        if member.status in ("left", "kicked"):
            await update.message.reply_text(
                "❌ Bot chưa được thêm vào nhóm này, hãy thêm bot vào nhóm trước rồi dùng /addgr."
            )
            return
    except Exception:
        # Nếu Telegram không cho check member (permission), vẫn cố lưu để owner quản lý.
        pass

    # Upsert -> active, approved_manually=1
    upsert_active_group(
        chat_id=chat_obj.id,
        chat_title=chat_obj.title,
        added_by_id=OWNER_ID,
        added_by_username="owner",
        status="active",
        approved_manually=1,
    )
    await update.message.reply_text(f"✅ Đã chấp nhận nhóm {chat_obj.title} (`{chat_obj.id}`)", parse_mode="Markdown")


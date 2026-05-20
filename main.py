"""
main.py — Entry point: đăng ký handler, chạy bot
"""
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from config import BOT_TOKEN
from database import init_db
from handlers import admin, ai_chat, caro, media, misc, events


async def _post_init(_application) -> None:
    media.start_download_worker()


def main():
    """Start bot"""
    print("🤖 Starting bot...")
    init_db()

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_post_init)
        .build()
    )

    # === Commands ===
    # Misc
    app.add_handler(CommandHandler("start",     misc.start))
    app.add_handler(CommandHandler("news",      misc.news))
    app.add_handler(CommandHandler("tt",        misc.weather))
    app.add_handler(CommandHandler("daoly",     misc.daoly))
    app.add_handler(CommandHandler("quiz",      misc.quiz))
    app.add_handler(CommandHandler("afk",       misc.afk))

    # Admin
    app.add_handler(CommandHandler("admins",    admin.admins))
    app.add_handler(CommandHandler("warn",      admin.warn))
    app.add_handler(CommandHandler("ban",       admin.ban))
    app.add_handler(CommandHandler("unban",     admin.unban))
    app.add_handler(CommandHandler("check",     admin.check_user))

    # AI Chat
    app.add_handler(CommandHandler("phienmoi",  ai_chat.reset_ai_session))
    app.add_handler(CommandHandler("model",     ai_chat.model_command))
    app.add_handler(CallbackQueryHandler(ai_chat.model_callback, pattern=r"^ai_model\|"))

    # Caro
    app.add_handler(CommandHandler("caro",      caro.caro_start))
    app.add_handler(CommandHandler("xo",        caro.xo_challenge))
    app.add_handler(CommandHandler("rank",      caro.rank_caro))
    app.add_handler(CommandHandler("set",       caro.set_caro_points))

    # Media
    app.add_handler(CommandHandler("download",  media.download_video))
    app.add_handler(CommandHandler("mp3",       media.download_mp3))

    # === Message events ===
    app.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        events.welcome_new_member
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        events.answer_handler
    ))

    # === Callback router ===
    app.add_handler(CallbackQueryHandler(caro.callback_router))

    print("✅ Bot is running!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

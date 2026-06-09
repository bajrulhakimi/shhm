from telegram.ext import Application, CommandHandler

from app.bot.handlers import (
    SCAN_COMMANDS,
    addwatch_command,
    analyze_command,
    error_handler,
    help_command,
    history_command,
    removewatch_command,
    scan_command,
    scan_status_command,
    settings_command,
    start,
    watchlist_command,
)


def build_telegram_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("analyze", analyze_command))
    for command in SCAN_COMMANDS:
        application.add_handler(CommandHandler(command, scan_command))
    application.add_handler(CommandHandler("scan_status", scan_status_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    application.add_handler(CommandHandler("addwatch", addwatch_command))
    application.add_handler(CommandHandler("removewatch", removewatch_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_error_handler(error_handler)
    return application

from telegram.ext import Application

telegram_application: Application | None = None


def set_telegram_application(application: Application | None) -> None:
    global telegram_application
    telegram_application = application

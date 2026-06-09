from telegram import ReplyKeyboardMarkup

MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["/analyze BBCA", "/scan_lq45"],
        ["/watchlist", "/history"],
        ["/settings", "/help"],
    ],
    resize_keyboard=True,
)


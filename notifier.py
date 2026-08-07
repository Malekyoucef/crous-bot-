from telegram import Bot
from config import BOT_TOKEN

# Create the bot instance
bot = Bot(token=BOT_TOKEN)


async def send_message(chat_id, text):
    """
    Send a Telegram message to one user.
    """
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            disable_web_page_preview=False,
        )
        print(f"Sent message to {chat_id}")

    except Exception as e:
        print(f"Failed to send message to {chat_id}: {e}")


async def send_to_all(subscribers, text):
    """
    Send a message to every subscriber.
    """
    for chat_id in subscribers:
        await send_message(chat_id, text)
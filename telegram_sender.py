from telegram import Bot
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)


async def send_message(chat_id, text):
    """
    Send a message to one Telegram user.
    """
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            disable_web_page_preview=False,
        )

        print(f"✅ Sent message to {chat_id}")

    except Exception as e:
        print(f"❌ Failed to send message to {chat_id}: {e}")


async def send_to_all(subscribers, text):
    """
    Send a message to every subscriber.
    """
    if not subscribers:
        print("No subscribers.")
        return

    print(f"Sending notification to {len(subscribers)} subscriber(s)...")

    for chat_id in subscribers:
        await send_message(chat_id, text)

    print("Finished sending notifications.")
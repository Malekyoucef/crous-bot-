import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from config import BOT_TOKEN
from database import (
    add_subscriber,
    remove_subscriber,
    get_subscribers,
    update_subscriber_region,
    toggle_restrict,
    get_active_rooms,
    add_or_update_room,
    mark_room_inactive
)
from scraper import get_available_rooms

# ==========================================
# 1. BOT COMMAND HANDLERS
# ==========================================
# (These remain exactly the same as the previous step)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    add_subscriber(chat_id)
    await update.message.reply_text("✅ You are now subscribed to CROUS alerts!\nUse `/setregion <city>` to select your region.", parse_mode='Markdown')

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    remove_subscriber(chat_id)
    await update.message.reply_text("❌ You have been unsubscribed.")

async def set_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please specify a region.\nExample: `/setregion paris`", parse_mode='Markdown')
        return
    region = " ".join(context.args)
    chat_id = update.effective_chat.id
    update_subscriber_region(chat_id, region)
    await update.message.reply_text(
        f"✅ Your preferred region has been set to: *{region}*\n"
        f"💡 _Tip: Use /restrict to hide all rooms that are not in this region._", 
        parse_mode='Markdown'
    )

async def restrict_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = get_subscribers()
    user_data = subs.get(chat_id)
    if not user_data or not user_data.get('region'):
        await update.message.reply_text("❌ Please set a region first using `/setregion <city>`.", parse_mode='Markdown')
        return
    is_now_restricted = toggle_restrict(chat_id)
    region = user_data['region']
    if is_now_restricted:
        await update.message.reply_text(f"🔒 Restriction *ENABLED*.\nYou will now ONLY receive notifications and see rooms in *{region}*.", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"🔓 Restriction *DISABLED*.\nYou will now see all rooms.", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subscribers = len(get_subscribers())
    await update.message.reply_text(
        f"🤖 CROUS Notifier\n\nCommands:\n/start - Subscribe\n/stop - Unsubscribe\n/setregion <city> - Select a region\n/restrict - Hide rooms not in your region\n/help - Show help\n/test - Test the bot\n/showall - Show all available rooms\n\nSubscribers: {subscribers}"
    )

async def showall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subs = get_subscribers()
    user_data = subs.get(chat_id, {})
    user_region = user_data.get('region')
    is_restricted = user_data.get('is_restricted', False)

    await update.message.reply_text("🔍 Checking CROUS...")
    rooms = await get_available_rooms()

    if not rooms:
        await update.message.reply_text("❌ No rooms available on the website right now.")
        return

    rooms_to_show = []
    for room in rooms:
        matches_region = user_region and (user_region.lower() in room['title'].lower())
        if user_region and is_restricted and not matches_region:
            continue
        rooms_to_show.append((room, matches_region))

    if not rooms_to_show:
        await update.message.reply_text(f"❌ No rooms currently available matching your restricted region: *{user_region}*", parse_mode='Markdown')
        return

    await update.message.reply_text(f"🏠 {len(rooms_to_show)} room(s) to show:")
    for room, matches_region in rooms_to_show:
        region_tag = f"✅ Matches your region: {user_region}\n" if matches_region else (f"⚠️ Not in {user_region}\n" if user_region else "")
        message = f"🏢 {room['title']}\n💶 {room['price']}\n{region_tag}\n{room['url']}"
        await update.message.reply_text(message, disable_web_page_preview=True)

async def test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is working!")


# ==========================================
# 2. BACKGROUND CHECKER (Tracking additions & removals)
# ==========================================

async def check_rooms(context: ContextTypes.DEFAULT_TYPE):
    print("Checking for new and removed CROUS rooms...")
    
    try:
        rooms = await get_available_rooms()
        subscribers = get_subscribers()
        
        # Get all rooms currently saved as 'active' in database
        active_in_db = get_active_rooms()
        
        # Convert fetched rooms to a dictionary {url: room_data}
        current_urls = {room["url"]: room for room in rooms}

        new_rooms = []
        removed_rooms = []

        # 1. FIND NEW ROOMS
        for url, room in current_urls.items():
            if url not in active_in_db:
                new_rooms.append(room)
            # Add or refresh room in DB
            add_or_update_room(url, room['title'], is_active=1)

        # 2. FIND REMOVED ROOMS
        for url, title in active_in_db.items():
            if url not in current_urls:
                removed_rooms.append({"url": url, "title": title})
                # Mark as inactive in DB so we don't notify again
                mark_room_inactive(url)

        # --- NOTIFY ABOUT NEW ROOMS ---
        if new_rooms:
            print(f"{len(new_rooms)} new room(s) found!")
            for room in new_rooms:
                for chat_id, user_data in subscribers.items():
                    user_region = user_data.get('region')
                    is_restricted = user_data.get('is_restricted', False)
                    matches_region = False
                    region_tag = ""
                    
                    if user_region:
                        matches_region = user_region.lower() in room['title'].lower()
                        if is_restricted and not matches_region:
                            continue
                        region_tag = f"✅ Matches your region: {user_region}\n" if matches_region else f"⚠️ Not in {user_region}\n"

                    message = f"🟢 *NEW CROUS ACCOMMODATION!*\n\n🏢 {room['title']}\n💶 {room['price']}\n{region_tag}\n🔗 {room['url']}"

                    try:
                        await context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True, parse_mode="Markdown")
                    except Exception as e:
                        print(f"Failed to send to {chat_id}: {e}")
                        
        # --- NOTIFY ABOUT REMOVED ROOMS ---
        if removed_rooms:
            print(f"{len(removed_rooms)} room(s) rented/removed!")
            for room in removed_rooms:
                for chat_id, user_data in subscribers.items():
                    user_region = user_data.get('region')
                    is_restricted = user_data.get('is_restricted', False)
                    
                    # Same logic: only send removal if they care about this region
                    if user_region:
                        matches_region = user_region.lower() in room['title'].lower()
                        if is_restricted and not matches_region:
                            continue

                    message = f"🔴 *ACCOMMODATION TAKEN/REMOVED*\n\n🏢 {room['title']}\nThis room is no longer available on the website."

                    try:
                        await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                    except Exception as e:
                        print(f"Failed to send to {chat_id}: {e}")

    except Exception as e:
        print(f"An error occurred while checking for rooms: {e}")


# ==========================================
# 3. MAIN APPLICATION STARTUP
# ==========================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("setregion", set_region))
    app.add_handler(CommandHandler("restrict", restrict_command))
    app.add_handler(CommandHandler("test", test))
    app.add_handler(CommandHandler("showall", showall))
    
    app.job_queue.run_repeating(check_rooms, interval=300, first=10)

    print("🤖 Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
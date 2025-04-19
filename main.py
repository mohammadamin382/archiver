
import os
from dotenv import load_dotenv
import telebot
from telebot import types
import logging
import sys
import threading
import schedule
import time

# Import modules
from modules.db_handler import setup_database, DatabaseManager
from modules.config_manager import ConfigManager
from modules.archive_manager import ArchiveManager
from modules.search_manager import SearchManager
from modules.user_manager import UserManager
from modules.backup_manager import BackupManager
from modules.message_handler import MessageHandler
from modules.utils import setup_logging

# Load environment variables
load_dotenv()

# Set up logging
logger = setup_logging()

# Check if token is provided
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    logger.error("No bot token provided. Please set the BOT_TOKEN environment variable.")
    sys.exit(1)

# Initialize bot
bot = telebot.TeleBot(TOKEN)
logger.info("Bot initialized")

# Setup database
db_manager = DatabaseManager()
if not setup_database(db_manager):
    logger.error("Failed to setup database. Exiting.")
    sys.exit(1)

# Initialize managers
config_manager = ConfigManager(db_manager)
archive_manager = ArchiveManager(bot, db_manager, config_manager)
search_manager = SearchManager(db_manager)
user_manager = UserManager(db_manager, config_manager)
backup_manager = BackupManager(db_manager, bot, config_manager)
message_handler = MessageHandler(bot, db_manager, config_manager)

# Set up message handlers
message_handler.setup_message_handlers()

# Start message handler
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    # Register user if not exists
    user_manager.register_user(user_id, username)
    
    # Check if bot is enabled for regular users
    if not config_manager.is_bot_enabled() and not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "🔴 ربات در حال حاضر غیر فعال است.")
        return
    
    # Create keyboard
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    
    # Different keyboards for admin and regular users
    if user_manager.is_admin(user_id):
        # Admin keyboard
        archive_btn = types.KeyboardButton("📦 تنظیم آرشیو جدید")
        search_btn = types.KeyboardButton("🔍 جستجو در آرشیو")
        manage_users_btn = types.KeyboardButton("👥 مدیریت کاربران")
        backup_btn = types.KeyboardButton("💾 پشتیبان‌گیری")
        settings_btn = types.KeyboardButton("⚙️ تنظیمات")
        markup.add(archive_btn, search_btn, manage_users_btn, backup_btn, settings_btn)
        
        bot.send_message(message.chat.id, 
                        "👋 سلام مدیر گرامی!\n\n"
                        "به ربات آرشیو پیشرفته خوش آمدید. از طریق دکمه‌های زیر می‌توانید ربات را مدیریت کنید:", 
                        reply_markup=markup)
    else:
        # Regular user keyboard
        search_btn = types.KeyboardButton("🔍 جستجو در آرشیو")
        help_btn = types.KeyboardButton("❓ راهنما")
        contact_admin_btn = types.KeyboardButton("📞 ارتباط با مدیر")
        markup.add(search_btn, help_btn, contact_admin_btn)
        
        bot.send_message(message.chat.id, 
                        "👋 سلام کاربر گرامی!\n\n"
                        "به ربات آرشیو پیشرفته خوش آمدید. از طریق دکمه‌های زیر می‌توانید از ربات استفاده کنید:", 
                        reply_markup=markup)

# Help command handler
@bot.message_handler(commands=['help'])
def help_command(message):
    show_help(message)

# Admin command handler
@bot.message_handler(commands=['admin'])
def admin_command(message):
    user_id = message.from_user.id
    
    if user_manager.is_admin(user_id):
        # Show admin menu
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        archive_btn = types.KeyboardButton("📦 تنظیم آرشیو جدید")
        search_btn = types.KeyboardButton("🔍 جستجو در آرشیو")
        manage_users_btn = types.KeyboardButton("👥 مدیریت کاربران")
        backup_btn = types.KeyboardButton("💾 پشتیبان‌گیری")
        settings_btn = types.KeyboardButton("⚙️ تنظیمات")
        markup.add(archive_btn, search_btn, manage_users_btn, backup_btn, settings_btn)
        
        bot.send_message(message.chat.id, 
                        "👑 پنل مدیریت:\n\n"
                        "از طریق دکمه‌های زیر می‌توانید ربات را مدیریت کنید:", 
                        reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ شما دسترسی مدیریت ندارید.")

# Text message handler
@bot.message_handler(func=lambda message: message.chat.type == 'private', content_types=['text'])
def handle_private_text_messages(message):
    user_id = message.from_user.id
    text = message.text
    
    # Check if bot is enabled for regular users
    if not config_manager.is_bot_enabled() and not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "🔴 ربات در حال حاضر غیر فعال است.")
        return
    
    # Admin commands
    if user_manager.is_admin(user_id):
        if text == "📦 تنظیم آرشیو جدید":
            archive_manager.start_archive_setup(message)
        elif text == "👥 مدیریت کاربران":
            user_manager.show_user_management(message)
        elif text == "💾 پشتیبان‌گیری":
            backup_manager.show_backup_options(message)
        elif text == "⚙️ تنظیمات":
            config_manager.show_settings(message)
        elif text == "🔍 جستجو در آرشیو":
            search_manager.start_search(message)
    
    # Commands for all users
    if text == "🔍 جستجو در آرشیو":
        search_manager.start_search(message)
    elif text == "❓ راهنما":
        show_help(message)
    elif text == "📞 ارتباط با مدیر":
        contact_admin(message)

def show_help(message):
    help_text = (
        "🔰 راهنمای استفاده از ربات آرشیو پیشرفته:\n\n"
        "🔍 جستجو در آرشیو: جستجو در پیام‌های آرشیو شده\n"
        "📞 ارتباط با مدیر: ارسال پیام به مدیر ربات\n\n"
        "✨ قابلیت‌های ربات:\n"
        "- آرشیو خودکار پیام‌های کانال‌ها و گروه‌ها\n"
        "- پشتیبانی از گروه‌های دارای موضوع (Topic)\n"
        "- فیلتر پیام‌ها براساس نوع، کلمات کلیدی و ...\n"
        "- جستجوی پیشرفته در آرشیو\n"
        "- پشتیبان‌گیری خودکار از دیتابیس\n"
        "- مدیریت دسترسی کاربران\n\n"
        "برای شروع، از دکمه‌های زیر استفاده کنید."
    )
    bot.send_message(message.chat.id, help_text)

def contact_admin(message):
    user_id = message.from_user.id
    user_manager.start_contact_admin(message)

# Error handler
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    # Check if bot is enabled for regular users
    if not config_manager.is_bot_enabled() and not user_manager.is_admin(user_id):
        bot.answer_callback_query(call.id, "🔴 ربات در حال حاضر غیر فعال است.")
        return
    
    # Extract callback data
    data = call.data
    
    try:
        # Route to appropriate handler
        if data.startswith('archive_'):
            archive_manager.handle_callback(call)
        elif data.startswith('search_'):
            search_manager.handle_callback(call)
        elif data.startswith('user_'):
            user_manager.handle_callback(call)
        elif data.startswith('backup_'):
            backup_manager.handle_callback(call)
        elif data.startswith('config_'):
            config_manager.handle_callback(call)
        else:
            logger.warning(f"Unknown callback data: {data}")
    except Exception as e:
        logger.error(f"Error handling callback: {e}", exc_info=True)
        bot.answer_callback_query(call.id, "❌ خطایی رخ داد. لطفاً دوباره تلاش کنید.")

def start_scheduler():
    """Start the scheduler for periodic tasks"""
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            logger.error(f"Error in scheduler: {e}", exc_info=True)
            time.sleep(5)  # Wait a bit longer on error

@bot.message_handler(content_types=['document'])
def handle_document(message):
    """Handle document uploads (for backup restoration)"""
    user_id = message.from_user.id
    
    # Only admins can restore backups
    if not user_manager.is_admin(user_id):
        return
        
    # Check if user is in restore flow
    # The backup manager will handle this if the user is in the right state

if __name__ == "__main__":
    try:
        # Start the scheduler in a separate thread
        scheduler_thread = threading.Thread(target=start_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        logger.info("Starting bot polling...")
        # Start the bot
        bot.polling(none_stop=True, interval=0)
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        sys.exit(1)

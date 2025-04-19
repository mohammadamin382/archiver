
import telebot
from telebot import types
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manager for bot configuration settings"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        
    def get_config(self, name, default=None):
        """Get configuration value by name"""
        result = self.db.fetch_one('telegram_archive_bot', 
                                "SELECT value FROM config WHERE name = %s", 
                                (name,))
        if result:
            return result['value']
        return default
        
    def set_config(self, name, value):
        """Set configuration value"""
        self.db.execute_query('telegram_archive_bot', 
                            "INSERT INTO config (name, value) VALUES (%s, %s) "
                            "ON DUPLICATE KEY UPDATE value = %s", 
                            (name, value, value))
        
    def is_bot_enabled(self):
        """Check if bot is enabled for regular users"""
        return self.get_config('bot_enabled', 'true').lower() == 'true'
        
    def show_settings(self, message):
        """Show bot settings menu"""
        bot = telebot.TeleBot.__self__
        
        # Create inline keyboard for settings
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # Bot status toggle
        bot_status = "🟢 فعال" if self.is_bot_enabled() else "🔴 غیرفعال"
        toggle_btn = types.InlineKeyboardButton(
            f"وضعیت ربات: {bot_status}", 
            callback_data="config_toggle_status"
        )
        
        # Backup settings
        backup_settings_btn = types.InlineKeyboardButton(
            "⚙️ تنظیمات پشتیبان‌گیری", 
            callback_data="config_backup_settings"
        )
        
        # Broadcast message
        broadcast_btn = types.InlineKeyboardButton(
            "📣 ارسال پیام همگانی", 
            callback_data="config_broadcast"
        )
        
        # Add buttons to markup
        markup.add(toggle_btn, backup_settings_btn, broadcast_btn)
        
        bot.send_message(
            message.chat.id, 
            "⚙️ تنظیمات ربات:\n\n"
            "از منوی زیر گزینه مورد نظر را انتخاب کنید.",
            reply_markup=markup
        )
        
    def handle_callback(self, call):
        """Handle callback queries for settings"""
        bot = telebot.TeleBot.__self__
        data = call.data
        
        if data == "config_toggle_status":
            # Toggle bot status
            current_status = self.is_bot_enabled()
            new_status = 'false' if current_status else 'true'
            self.set_config('bot_enabled', new_status)
            
            status_text = "🟢 فعال" if new_status == 'true' else "🔴 غیرفعال"
            bot.answer_callback_query(
                call.id, 
                f"وضعیت ربات به {status_text} تغییر کرد."
            )
            
            # Update inline keyboard
            self.update_settings_keyboard(call.message)
            
        elif data == "config_backup_settings":
            # Show backup settings
            self.show_backup_settings(call.message)
            
        elif data == "config_broadcast":
            # Start broadcast message flow
            bot.answer_callback_query(call.id, "لطفا پیام خود را ارسال کنید.")
            bot.send_message(
                call.message.chat.id,
                "📣 ارسال پیام همگانی:\n\n"
                "لطفا پیام خود را ارسال کنید. این پیام برای تمام کاربران ربات ارسال خواهد شد."
            )
            # Set user state to waiting for broadcast message
            bot.register_next_step_handler(call.message, self.process_broadcast_message)
            
        elif data.startswith("config_set_backup_interval_"):
            # Set backup interval
            interval = data.split("_")[-1]
            self.set_config('backup_interval', interval)
            bot.answer_callback_query(
                call.id, 
                f"بازه زمانی پشتیبان‌گیری به {interval} دقیقه تنظیم شد."
            )
            self.show_backup_settings(call.message)
            
    def update_settings_keyboard(self, message):
        """Update settings keyboard with current values"""
        bot = telebot.TeleBot.__self__
        
        # Create updated inline keyboard
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # Bot status toggle with updated status
        bot_status = "🟢 فعال" if self.is_bot_enabled() else "🔴 غیرفعال"
        toggle_btn = types.InlineKeyboardButton(
            f"وضعیت ربات: {bot_status}", 
            callback_data="config_toggle_status"
        )
        
        # Backup settings
        backup_settings_btn = types.InlineKeyboardButton(
            "⚙️ تنظیمات پشتیبان‌گیری", 
            callback_data="config_backup_settings"
        )
        
        # Broadcast message
        broadcast_btn = types.InlineKeyboardButton(
            "📣 ارسال پیام همگانی", 
            callback_data="config_broadcast"
        )
        
        # Add buttons to markup
        markup.add(toggle_btn, backup_settings_btn, broadcast_btn)
        
        # Edit message with updated keyboard
        bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=markup
        )
        
    def show_backup_settings(self, message):
        """Show backup settings menu"""
        bot = telebot.TeleBot.__self__
        
        # Get current backup interval
        current_interval = self.get_config('backup_interval', '1440')
        
        # Create inline keyboard for backup settings
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Interval options
        interval_30m = types.InlineKeyboardButton(
            "30 دقیقه", 
            callback_data="config_set_backup_interval_30"
        )
        interval_1h = types.InlineKeyboardButton(
            "1 ساعت", 
            callback_data="config_set_backup_interval_60"
        )
        interval_6h = types.InlineKeyboardButton(
            "6 ساعت", 
            callback_data="config_set_backup_interval_360"
        )
        interval_12h = types.InlineKeyboardButton(
            "12 ساعت", 
            callback_data="config_set_backup_interval_720"
        )
        interval_24h = types.InlineKeyboardButton(
            "24 ساعت", 
            callback_data="config_set_backup_interval_1440"
        )
        
        # Back button
        back_btn = types.InlineKeyboardButton(
            "🔙 بازگشت", 
            callback_data="config_back_to_settings"
        )
        
        # Add buttons to markup
        markup.add(interval_30m, interval_1h, interval_6h, interval_12h, interval_24h, back_btn)
        
        # Calculate human-readable interval
        interval_text = ""
        interval_mins = int(current_interval)
        if interval_mins < 60:
            interval_text = f"{interval_mins} دقیقه"
        elif interval_mins < 1440:
            interval_text = f"{interval_mins // 60} ساعت"
        else:
            interval_text = f"{interval_mins // 1440} روز"
        
        bot.send_message(
            message.chat.id, 
            f"⚙️ تنظیمات پشتیبان‌گیری:\n\n"
            f"بازه زمانی فعلی: {interval_text}\n\n"
            "بازه زمانی جدید را انتخاب کنید:",
            reply_markup=markup
        )
        
    def process_broadcast_message(self, message):
        """Process broadcast message from admin"""
        bot = telebot.TeleBot.__self__
        
        # Get all users
        users = self.db.fetch_all('telegram_archive_bot', "SELECT user_id FROM users")
        
        if not users:
            bot.send_message(
                message.chat.id,
                "❌ هیچ کاربری در سیستم ثبت نشده است."
            )
            return
        
        # Send confirmation
        markup = types.InlineKeyboardMarkup(row_width=2)
        confirm_btn = types.InlineKeyboardButton(
            "✅ ارسال", 
            callback_data="config_confirm_broadcast"
        )
        cancel_btn = types.InlineKeyboardButton(
            "❌ انصراف", 
            callback_data="config_cancel_broadcast"
        )
        markup.add(confirm_btn, cancel_btn)
        
        # Store message text temporarily
        self.broadcast_message = message.text
        self.user_count = len(users)
        
        bot.send_message(
            message.chat.id,
            f"📣 پیش‌نمایش پیام:\n\n"
            f"{message.text}\n\n"
            f"این پیام برای {len(users)} کاربر ارسال خواهد شد. آیا مطمئن هستید؟",
            reply_markup=markup
        )

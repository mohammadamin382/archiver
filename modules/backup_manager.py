
import os
import telebot
from telebot import types
import datetime
import zipfile
import logging
import schedule
import time
import json

logger = logging.getLogger(__name__)

class BackupManager:
    """Manager for database backup operations"""
    
    def __init__(self, db_manager, bot, config_manager):
        self.db = db_manager
        self.bot = bot
        self.config = config_manager
        self.backup_dir = "backups"
        
        # Create backup directory if it doesn't exist
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            
        # Setup scheduled backups if interval is set
        self.setup_scheduled_backups()
        
    def setup_scheduled_backups(self):
        """Setup scheduled backups based on config"""
        # Clear any existing backup jobs
        schedule.clear('backup')
        
        # Get backup interval from config
        interval = int(self.config.get_config('backup_interval', '1440'))  # Default to 24 hours
        
        if interval > 0:
            # Schedule backup based on interval
            schedule.every(interval).minutes.do(self.auto_backup).tag('backup')
            logger.info(f"Scheduled automatic backups every {interval} minutes")
            
    def show_backup_options(self, message):
        """Show backup options menu"""
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        manual_backup_btn = types.InlineKeyboardButton(
            "💾 پشتیبان‌گیری دستی", 
            callback_data="backup_manual"
        )
        
        auto_backup_btn = types.InlineKeyboardButton(
            "⏱️ تنظیم پشتیبان‌گیری خودکار", 
            callback_data="backup_auto_setup"
        )
        
        restore_btn = types.InlineKeyboardButton(
            "🔄 بازیابی از پشتیبان", 
            callback_data="backup_restore"
        )
        
        list_backups_btn = types.InlineKeyboardButton(
            "📋 لیست فایل‌های پشتیبان", 
            callback_data="backup_list"
        )
        
        markup.add(manual_backup_btn, auto_backup_btn, restore_btn, list_backups_btn)
        
        self.bot.send_message(
            message.chat.id,
            "💾 مدیریت پشتیبان‌گیری:\n\n"
            "از منوی زیر گزینه مورد نظر را انتخاب کنید:",
            reply_markup=markup
        )
        
    def handle_callback(self, call):
        """Handle callback queries for backup operations"""
        data = call.data
        
        if data == "backup_manual":
            # Create manual backup
            self.bot.answer_callback_query(call.id, "در حال تهیه پشتیبان...")
            backup_file = self.create_backup()
            
            if backup_file:
                # Send backup file
                with open(backup_file, 'rb') as f:
                    self.bot.send_document(
                        call.message.chat.id,
                        f,
                        caption="💾 فایل پشتیبان با موفقیت ایجاد شد."
                    )
            else:
                self.bot.send_message(
                    call.message.chat.id,
                    "❌ خطا در ایجاد فایل پشتیبان."
                )
                
        elif data == "backup_auto_setup":
            # Show automatic backup setup
            self.show_auto_backup_setup(call.message)
            
        elif data == "backup_restore":
            # Show restore options
            self.bot.answer_callback_query(call.id, "لطفاً فایل پشتیبان را ارسال کنید.")
            self.bot.send_message(
                call.message.chat.id,
                "🔄 بازیابی از پشتیبان:\n\n"
                "لطفاً فایل پشتیبان (zip) را ارسال کنید."
            )
            self.bot.register_next_step_handler(call.message, self.process_restore_file)
            
        elif data == "backup_list":
            # Show list of backup files
            self.show_backup_list(call.message)
            
        elif data.startswith("backup_set_interval_"):
            # Set backup interval
            interval = data.split("_")[-1]
            self.set_backup_interval(call, interval)
            
        elif data.startswith("backup_set_channel_"):
            # Set backup channel
            self.bot.answer_callback_query(call.id, "لطفاً شناسه کانال گزارشات را وارد کنید.")
            self.bot.send_message(
                call.message.chat.id,
                "⏱️ تنظیم کانال گزارشات پشتیبان‌گیری:\n\n"
                "لطفاً شناسه کانال (مانند -1001234567890) را وارد کنید.\n"
                "توجه: ربات باید در کانال ادمین باشد."
            )
            self.bot.register_next_step_handler(call.message, self.process_backup_channel)
            
        elif data.startswith("backup_download_"):
            # Download specific backup file
            filename = data.split("backup_download_")[-1]
            self.download_backup(call.message, filename)
            
        elif data.startswith("backup_delete_"):
            # Delete specific backup file
            filename = data.split("backup_delete_")[-1]
            self.delete_backup(call, filename)
            
    def show_auto_backup_setup(self, message):
        """Show automatic backup setup options"""
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Get current backup interval
        current_interval = self.config.get_config('backup_interval', '1440')
        
        # Interval options
        interval_30m = types.InlineKeyboardButton(
            "30 دقیقه", 
            callback_data="backup_set_interval_30"
        )
        
        interval_1h = types.InlineKeyboardButton(
            "1 ساعت", 
            callback_data="backup_set_interval_60"
        )
        
        interval_6h = types.InlineKeyboardButton(
            "6 ساعت", 
            callback_data="backup_set_interval_360"
        )
        
        interval_12h = types.InlineKeyboardButton(
            "12 ساعت", 
            callback_data="backup_set_interval_720"
        )
        
        interval_24h = types.InlineKeyboardButton(
            "24 ساعت", 
            callback_data="backup_set_interval_1440"
        )
        
        disable_btn = types.InlineKeyboardButton(
            "غیرفعال کردن", 
            callback_data="backup_set_interval_0"
        )
        
        # Set channel button
        channel_btn = types.InlineKeyboardButton(
            "📢 تنظیم کانال گزارشات", 
            callback_data="backup_set_channel_"
        )
        
        # Back button
        back_btn = types.InlineKeyboardButton(
            "🔙 بازگشت", 
            callback_data="backup_back_to_menu"
        )
        
        # Calculate human-readable interval
        interval_text = self.get_interval_text(int(current_interval))
        
        # Add buttons to markup
        markup.add(interval_30m, interval_1h, interval_6h, interval_12h, interval_24h, disable_btn, channel_btn, back_btn)
        
        # Get backup channel info
        backup_channel = self.config.get_config('backup_channel_id', '')
        channel_text = f"تنظیم شده: {backup_channel}" if backup_channel else "تنظیم نشده"
        
        self.bot.send_message(
            message.chat.id,
            f"⏱️ تنظیم پشتیبان‌گیری خودکار:\n\n"
            f"بازه زمانی فعلی: {interval_text}\n"
            f"کانال گزارشات: {channel_text}\n\n"
            f"بازه زمانی جدید را انتخاب کنید:",
            reply_markup=markup
        )
        
    def set_backup_interval(self, call, interval):
        """Set backup interval in minutes"""
        interval_int = int(interval)
        
        # Update config
        self.config.set_config('backup_interval', interval)
        
        # Setup scheduled backups
        self.setup_scheduled_backups()
        
        # Show confirmation
        interval_text = self.get_interval_text(interval_int)
        self.bot.answer_callback_query(
            call.id, 
            f"✅ بازه زمانی پشتیبان‌گیری به {interval_text} تنظیم شد."
        )
        
        # Show updated auto backup setup
        self.show_auto_backup_setup(call.message)
        
    def process_backup_channel(self, message):
        """Process backup channel ID input"""
        channel_id = message.text.strip()
        
        # Validate channel ID format
        if not (channel_id.startswith('-100') and channel_id[4:].isdigit()):
            self.bot.send_message(
                message.chat.id,
                "❌ فرمت شناسه کانال نامعتبر است. لطفاً دوباره تلاش کنید."
            )
            self.bot.register_next_step_handler(message, self.process_backup_channel)
            return
            
        # Try to send a test message to the channel
        try:
            self.bot.send_message(
                channel_id,
                "✅ این یک پیام تست است. تنظیمات کانال گزارشات پشتیبان‌گیری با موفقیت انجام شد."
            )
            
            # Update config
            self.config.set_config('backup_channel_id', channel_id)
            
            self.bot.send_message(
                message.chat.id,
                "✅ کانال گزارشات پشتیبان‌گیری با موفقیت تنظیم شد."
            )
            
            # Show auto backup setup again
            self.show_auto_backup_setup(message)
            
        except Exception as e:
            logger.error(f"Error setting backup channel: {e}")
            self.bot.send_message(
                message.chat.id,
                "❌ خطا در تنظیم کانال گزارشات. لطفاً مطمئن شوید که:\n"
                "1. شناسه کانال صحیح است.\n"
                "2. ربات در کانال عضو است.\n"
                "3. ربات در کانال ادمین است."
            )
            
    def create_backup(self):
        """Create a full database backup"""
        try:
            # Get current timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"telegram_archive_bot_backup_{timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Create zip file
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add database dumps
                self.add_database_dumps(zipf)
                
                # Add config info
                self.add_config_info(zipf)
                
            # Log backup in database
            self.log_backup(backup_filename, os.path.getsize(backup_path), 'success')
            
            logger.info(f"Backup created successfully: {backup_filename}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            # Log error in database
            self.log_backup('', 0, 'failed', str(e))
            return None
            
    def add_database_dumps(self, zipf):
        """Add database dumps to zip file"""
        # Dump telegram_archive_bot database
        tables = [
            'users', 'config', 'sources', 'permissions', 
            'archived_messages', 'backup_logs'
        ]
        
        for table in tables:
            # Fetch all data from table
            rows = self.db.fetch_all('telegram_archive_bot', f"SELECT * FROM {table}")
            
            if rows:
                # Convert to JSON
                json_data = json.dumps(rows, default=str, ensure_ascii=False, indent=2)
                
                # Add to zip
                zipf.writestr(f"database/{table}.json", json_data)
                
    def add_config_info(self, zipf):
        """Add config info to zip file"""
        # Get all config values
        config_rows = self.db.fetch_all('telegram_archive_bot', "SELECT * FROM config")
        
        if config_rows:
            # Convert to JSON
            config_json = json.dumps(config_rows, default=str, ensure_ascii=False, indent=2)
            
            # Add to zip
            zipf.writestr("config.json", config_json)
            
    def log_backup(self, file_name, file_size, status, message=''):
        """Log backup operation in database"""
        self.db.execute_query('telegram_archive_bot', '''
            INSERT INTO backup_logs (file_name, file_size, status, message)
            VALUES (%s, %s, %s, %s)
        ''', (file_name, file_size, status, message))
        
    def process_restore_file(self, message):
        """Process restore file upload"""
        # Check if message contains a document
        if not message.document:
            self.bot.send_message(
                message.chat.id,
                "❌ لطفاً یک فایل zip ارسال کنید."
            )
            return
            
        # Check file extension
        file_name = message.document.file_name
        if not file_name.endswith('.zip'):
            self.bot.send_message(
                message.chat.id,
                "❌ فایل باید از نوع zip باشد."
            )
            return
            
        # Download file
        self.bot.send_message(
            message.chat.id,
            "🔄 در حال دریافت فایل پشتیبان... لطفاً منتظر بمانید."
        )
        
        file_info = self.bot.get_file(message.document.file_id)
        downloaded_file = self.bot.download_file(file_info.file_path)
        
        # Save file temporarily
        temp_path = os.path.join(self.backup_dir, "temp_restore.zip")
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file)
            
        # Ask for confirmation
        markup = types.InlineKeyboardMarkup(row_width=2)
        confirm_btn = types.InlineKeyboardButton("✅ بله، بازیابی شود", callback_data="backup_restore_confirm")
        cancel_btn = types.InlineKeyboardButton("❌ خیر، انصراف", callback_data="backup_restore_cancel")
        markup.add(confirm_btn, cancel_btn)
        
        self.bot.send_message(
            message.chat.id,
            "⚠️ هشدار: بازیابی از پشتیبان باعث حذف تمام اطلاعات فعلی و جایگزینی با اطلاعات پشتیبان می‌شود.\n\n"
            "آیا از بازیابی اطمینان دارید؟",
            reply_markup=markup
        )
        
    def auto_backup(self):
        """Perform automatic backup"""
        logger.info("Starting automatic backup...")
        
        # Create backup
        backup_file = self.create_backup()
        
        if not backup_file:
            logger.error("Automatic backup failed")
            return
            
        # Get backup channel ID
        channel_id = self.config.get_config('backup_channel_id')
        
        if channel_id:
            try:
                # Send backup file to channel
                with open(backup_file, 'rb') as f:
                    self.bot.send_document(
                        channel_id,
                        f,
                        caption="🔄 پشتیبان خودکار ربات آرشیو"
                    )
                    
                logger.info(f"Automatic backup sent to channel: {channel_id}")
                
            except Exception as e:
                logger.error(f"Error sending automatic backup to channel: {e}")
                
        # Keep only the last 10 backup files
        self.cleanup_old_backups()
                
    def cleanup_old_backups(self, keep_count=10):
        """Clean up old backup files, keeping the most recent ones"""
        backup_files = []
        
        for filename in os.listdir(self.backup_dir):
            if filename.startswith("telegram_archive_bot_backup_") and filename.endswith(".zip"):
                filepath = os.path.join(self.backup_dir, filename)
                backup_files.append((filepath, os.path.getmtime(filepath)))
                
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x[1], reverse=True)
        
        # Delete older files
        if len(backup_files) > keep_count:
            for filepath, _ in backup_files[keep_count:]:
                try:
                    os.remove(filepath)
                    logger.info(f"Deleted old backup: {filepath}")
                except Exception as e:
                    logger.error(f"Error deleting old backup {filepath}: {e}")
                    
    def show_backup_list(self, message):
        """Show list of backup files"""
        backup_files = []
        
        for filename in os.listdir(self.backup_dir):
            if filename.startswith("telegram_archive_bot_backup_") and filename.endswith(".zip"):
                filepath = os.path.join(self.backup_dir, filename)
                backup_files.append((filename, os.path.getmtime(filepath), os.path.getsize(filepath)))
                
        if not backup_files:
            self.bot.send_message(
                message.chat.id,
                "📂 هیچ فایل پشتیبانی یافت نشد."
            )
            return
            
        # Sort by modification time (newest first)
        backup_files.sort(key=lambda x: x[1], reverse=True)
        
        # Create message
        text = "📋 لیست فایل‌های پشتیبان:\n\n"
        
        for idx, (filename, mtime, size) in enumerate(backup_files[:10], start=1):
            # Format date
            date = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            # Format size
            size_kb = size / 1024
            size_text = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
            
            text += f"{idx}. 📦 {filename}\n"
            text += f"   📅 {date}\n"
            text += f"   📊 {size_text}\n\n"
            
        if len(backup_files) > 10:
            text += f"... و {len(backup_files) - 10} فایل دیگر\n"
            
        # Create inline keyboard for actions
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for filename, _, _ in backup_files[:5]:
            # Download button
            download_btn = types.InlineKeyboardButton(
                f"📥 {filename[:15]}...",
                callback_data=f"backup_download_{filename}"
            )
            
            # Delete button
            delete_btn = types.InlineKeyboardButton(
                "🗑️",
                callback_data=f"backup_delete_{filename}"
            )
            
            markup.row(download_btn, delete_btn)
            
        # Back button
        back_btn = types.InlineKeyboardButton("🔙 بازگشت", callback_data="backup_back_to_menu")
        markup.add(back_btn)
        
        self.bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup
        )
        
    def download_backup(self, message, filename):
        """Send a backup file to the user"""
        filepath = os.path.join(self.backup_dir, filename)
        
        if not os.path.exists(filepath):
            self.bot.send_message(
                message.chat.id,
                "❌ فایل پشتیبان یافت نشد."
            )
            return
            
        # Send file
        with open(filepath, 'rb') as f:
            self.bot.send_document(
                message.chat.id,
                f,
                caption=f"📥 فایل پشتیبان: {filename}"
            )
            
    def delete_backup(self, call, filename):
        """Delete a backup file"""
        filepath = os.path.join(self.backup_dir, filename)
        
        if not os.path.exists(filepath):
            self.bot.answer_callback_query(call.id, "❌ فایل پشتیبان یافت نشد.")
            return
            
        # Delete file
        try:
            os.remove(filepath)
            self.bot.answer_callback_query(call.id, "✅ فایل پشتیبان با موفقیت حذف شد.")
            
            # Update backup list
            self.show_backup_list(call.message)
            
        except Exception as e:
            logger.error(f"Error deleting backup {filepath}: {e}")
            self.bot.answer_callback_query(call.id, "❌ خطا در حذف فایل پشتیبان.")
            
    def get_interval_text(self, interval_mins):
        """Get human-readable interval text"""
        if interval_mins == 0:
            return "غیرفعال"
        elif interval_mins < 60:
            return f"{interval_mins} دقیقه"
        elif interval_mins < 1440:
            return f"{interval_mins // 60} ساعت"
        else:
            return f"{interval_mins // 1440} روز"

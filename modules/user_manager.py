
import telebot
from telebot import types
import logging

logger = logging.getLogger(__name__)

class UserManager:
    """Manager for user administration and permissions"""
    
    def __init__(self, db_manager, config_manager):
        self.db = db_manager
        self.config = config_manager
        self.contact_states = {}  # Store user contact states
        
    def register_user(self, user_id, username):
        """Register a new user or update existing one"""
        try:
            self.db.execute_query('telegram_archive_bot', '''
                INSERT INTO users (user_id, username) 
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE username = %s
            ''', (user_id, username, username))
            return True
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return False
            
    def is_admin(self, user_id):
        """Check if user is an admin"""
        result = self.db.fetch_one('telegram_archive_bot', '''
            SELECT is_admin FROM users WHERE user_id = %s
        ''', (user_id,))
        
        if result:
            return result['is_admin']
        return False
        
    def show_user_management(self, message):
        """Show user management menu"""
        bot = telebot.TeleBot.__self__
        
        # Create inline keyboard
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # List users button
        list_users_btn = types.InlineKeyboardButton(
            "👥 لیست کاربران", 
            callback_data="user_list"
        )
        
        # Add admin button
        add_admin_btn = types.InlineKeyboardButton(
            "👑 افزودن مدیر جدید", 
            callback_data="user_add_admin"
        )
        
        # Manage permissions button
        permissions_btn = types.InlineKeyboardButton(
            "🔒 مدیریت دسترسی‌ها", 
            callback_data="user_manage_permissions"
        )
        
        # Add buttons to markup
        markup.add(list_users_btn, add_admin_btn, permissions_btn)
        
        bot.send_message(
            message.chat.id, 
            "👥 مدیریت کاربران:\n\n"
            "از منوی زیر گزینه مورد نظر را انتخاب کنید:",
            reply_markup=markup
        )
        
    def handle_callback(self, call):
        """Handle callback queries for user management"""
        bot = telebot.TeleBot.__self__
        data = call.data
        
        if data == "user_list":
            # Show user list
            self.show_user_list(call.message)
            
        elif data == "user_add_admin":
            # Start add admin flow
            bot.answer_callback_query(call.id, "لطفاً شناسه کاربری مدیر جدید را وارد کنید.")
            bot.send_message(
                call.message.chat.id,
                "👑 افزودن مدیر جدید:\n\n"
                "لطفاً شناسه کاربری (user_id) مدیر جدید را وارد کنید:"
            )
            bot.register_next_step_handler(call.message, self.process_add_admin)
            
        elif data == "user_manage_permissions":
            # Show sources to manage permissions
            self.show_sources_for_permissions(call.message)
            
        elif data.startswith("user_view_"):
            # View user details
            user_id = int(data.split("_")[-1])
            self.show_user_details(call.message, user_id)
            
        elif data.startswith("user_toggle_admin_"):
            # Toggle admin status
            user_id = int(data.split("_")[-1])
            self.toggle_admin_status(call, user_id)
            
        elif data.startswith("user_permissions_source_"):
            # Manage permissions for a source
            source_id = int(data.split("_")[-1])
            self.show_source_permissions(call.message, source_id)
            
        elif data.startswith("user_grant_"):
            # Grant permission to user
            parts = data.split("_")
            source_id = int(parts[-2])
            user_id = int(parts[-1])
            self.toggle_user_permission(call, source_id, user_id)
            
    def show_user_list(self, message):
        """Show list of users"""
        bot = telebot.TeleBot.__self__
        
        # Get all users
        users = self.db.fetch_all('telegram_archive_bot', '''
            SELECT * FROM users ORDER BY is_admin DESC, created_at DESC
        ''')
        
        if not users:
            bot.send_message(
                message.chat.id,
                "❌ هیچ کاربری در سیستم ثبت نشده است."
            )
            return
            
        # Create message text
        text = "👥 لیست کاربران:\n\n"
        
        for idx, user in enumerate(users, start=1):
            admin_status = "👑 مدیر" if user['is_admin'] else "👤 کاربر عادی"
            text += f"{idx}. {admin_status} | {user['username']} ({user['user_id']})\n"
            
        # Create inline keyboard for user details
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        for user in users:
            user_btn = types.InlineKeyboardButton(
                f"{'👑 ' if user['is_admin'] else ''}{user['username']}",
                callback_data=f"user_view_{user['user_id']}"
            )
            markup.add(user_btn)
            
        # Back button
        back_btn = types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="user_back_to_management"
        )
        markup.add(back_btn)
        
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup
        )
        
    def process_add_admin(self, message):
        """Process add admin input"""
        bot = telebot.TeleBot.__self__
        user_id_text = message.text.strip()
        
        # Validate user ID
        if not user_id_text.isdigit():
            bot.send_message(
                message.chat.id,
                "❌ شناسه کاربری باید عدد باشد. لطفاً دوباره تلاش کنید."
            )
            bot.register_next_step_handler(message, self.process_add_admin)
            return
            
        user_id = int(user_id_text)
        
        # Check if user exists
        user = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM users WHERE user_id = %s
        ''', (user_id,))
        
        if user:
            if user['is_admin']:
                bot.send_message(
                    message.chat.id,
                    f"❌ کاربر {user['username']} ({user_id}) در حال حاضر مدیر است."
                )
            else:
                # Make user admin
                self.db.execute_query('telegram_archive_bot', '''
                    UPDATE users SET is_admin = TRUE WHERE user_id = %s
                ''', (user_id,))
                
                bot.send_message(
                    message.chat.id,
                    f"✅ کاربر {user['username']} ({user_id}) با موفقیت به عنوان مدیر ثبت شد."
                )
        else:
            # Register new admin
            self.db.execute_query('telegram_archive_bot', '''
                INSERT INTO users (user_id, username, is_admin) 
                VALUES (%s, %s, TRUE)
            ''', (user_id, f"Admin_{user_id}"))
            
            bot.send_message(
                message.chat.id,
                f"✅ کاربر جدید با شناسه {user_id} با موفقیت به عنوان مدیر ثبت شد."
            )
            
        # Show user management menu again
        self.show_user_management(message)
        
    def show_user_details(self, message, user_id):
        """Show user details"""
        bot = telebot.TeleBot.__self__
        
        # Get user details
        user = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM users WHERE user_id = %s
        ''', (user_id,))
        
        if not user:
            bot.send_message(
                message.chat.id,
                "❌ کاربر مورد نظر یافت نشد."
            )
            return
            
        # Get user permissions
        permissions = self.db.fetch_all('telegram_archive_bot', '''
            SELECT p.*, s.chat_title FROM permissions p
            JOIN sources s ON p.source_id = s.id
            WHERE p.user_id = %s
        ''', (user_id,))
        
        # Create message text
        admin_status = "👑 مدیر" if user['is_admin'] else "👤 کاربر عادی"
        text = f"👤 جزئیات کاربر:\n\n"
        text += f"🔸 نام کاربری: {user['username']}\n"
        text += f"🔸 شناسه: {user['user_id']}\n"
        text += f"🔸 وضعیت: {admin_status}\n"
        text += f"🔸 تاریخ ثبت: {user['created_at']}\n\n"
        
        # Add permissions info
        if permissions:
            text += "🔒 دسترسی‌ها:\n"
            for p in permissions:
                status = "✅" if p['can_search'] else "❌"
                text += f"  • {p['chat_title']}: {status}\n"
        else:
            text += "🔒 دسترسی‌ها: هیچ دسترسی خاصی ثبت نشده است.\n"
            
        # Create inline keyboard for actions
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        # Toggle admin status button
        if not user['is_admin']:
            admin_btn = types.InlineKeyboardButton(
                "👑 ارتقا به مدیر",
                callback_data=f"user_toggle_admin_{user_id}"
            )
            markup.add(admin_btn)
        elif user['user_id'] != message.chat.id:  # Don't allow demoting yourself
            admin_btn = types.InlineKeyboardButton(
                "👤 تنزل به کاربر عادی",
                callback_data=f"user_toggle_admin_{user_id}"
            )
            markup.add(admin_btn)
            
        # Back button
        back_btn = types.InlineKeyboardButton(
            "🔙 بازگشت به لیست کاربران",
            callback_data="user_list"
        )
        markup.add(back_btn)
        
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup
        )
        
    def toggle_admin_status(self, call, user_id):
        """Toggle admin status for a user"""
        bot = telebot.TeleBot.__self__
        admin_user_id = call.from_user.id
        
        # Prevent demoting yourself
        if user_id == admin_user_id:
            bot.answer_callback_query(call.id, "❌ شما نمی‌توانید وضعیت مدیر خود را تغییر دهید.")
            return
            
        # Get user details
        user = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM users WHERE user_id = %s
        ''', (user_id,))
        
        if not user:
            bot.answer_callback_query(call.id, "❌ کاربر مورد نظر یافت نشد.")
            return
            
        # Toggle admin status
        new_status = not user['is_admin']
        self.db.execute_query('telegram_archive_bot', '''
            UPDATE users SET is_admin = %s WHERE user_id = %s
        ''', (new_status, user_id))
        
        status_text = "مدیر" if new_status else "کاربر عادی"
        bot.answer_callback_query(call.id, f"✅ وضعیت کاربر به {status_text} تغییر کرد.")
        
        # Show updated user details
        self.show_user_details(call.message, user_id)
        
    def show_sources_for_permissions(self, message):
        """Show list of sources to manage permissions"""
        bot = telebot.TeleBot.__self__
        
        # Get all sources
        sources = self.db.fetch_all('telegram_archive_bot', '''
            SELECT * FROM sources ORDER BY id
        ''')
        
        if not sources:
            bot.send_message(
                message.chat.id,
                "❌ هیچ منبعی برای مدیریت دسترسی‌ها ثبت نشده است."
            )
            return
            
        # Create message text
        text = "🔒 مدیریت دسترسی‌ها:\n\n"
        text += "لطفاً منبع مورد نظر را انتخاب کنید:"
        
        # Create inline keyboard for sources
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for source in sources:
            source_text = f"{source['chat_title']} ({self.get_source_type_persian(source['type'])})"
            source_btn = types.InlineKeyboardButton(
                source_text,
                callback_data=f"user_permissions_source_{source['id']}"
            )
            markup.add(source_btn)
            
        # Back button
        back_btn = types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="user_back_to_management"
        )
        markup.add(back_btn)
        
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup
        )
        
    def show_source_permissions(self, message, source_id):
        """Show permissions for a source"""
        bot = telebot.TeleBot.__self__
        
        # Get source details
        source = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM sources WHERE id = %s
        ''', (source_id,))
        
        if not source:
            bot.send_message(
                message.chat.id,
                "❌ منبع مورد نظر یافت نشد."
            )
            return
            
        # Get all users and their permissions for this source
        users = self.db.fetch_all('telegram_archive_bot', '''
            SELECT u.*, p.can_search FROM users u
            LEFT JOIN permissions p ON u.user_id = p.user_id AND p.source_id = %s
            WHERE u.is_admin = FALSE
            ORDER BY u.username
        ''', (source_id,))
        
        if not users:
            bot.send_message(
                message.chat.id,
                "❌ هیچ کاربر عادی در سیستم ثبت نشده است."
            )
            return
            
        # Create message text
        text = f"🔒 مدیریت دسترسی‌ها برای {source['chat_title']}:\n\n"
        text += "برای تغییر دسترسی، روی کاربر مورد نظر کلیک کنید:"
        
        # Create inline keyboard for users
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for user in users:
            status = "✅" if user['can_search'] else "❌"
            user_text = f"{status} {user['username']} ({user['user_id']})"
            user_btn = types.InlineKeyboardButton(
                user_text,
                callback_data=f"user_grant_{source_id}_{user['user_id']}"
            )
            markup.add(user_btn)
            
        # Back button
        back_btn = types.InlineKeyboardButton(
            "🔙 بازگشت",
            callback_data="user_manage_permissions"
        )
        markup.add(back_btn)
        
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup
        )
        
    def toggle_user_permission(self, call, source_id, user_id):
        """Toggle search permission for a user on a source"""
        bot = telebot.TeleBot.__self__
        
        # Check if permission exists
        permission = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM permissions WHERE user_id = %s AND source_id = %s
        ''', (user_id, source_id))
        
        if permission:
            # Toggle existing permission
            new_status = not permission['can_search']
            self.db.execute_query('telegram_archive_bot', '''
                UPDATE permissions SET can_search = %s
                WHERE user_id = %s AND source_id = %s
            ''', (new_status, user_id, source_id))
        else:
            # Create new permission (granted by default)
            self.db.execute_query('telegram_archive_bot', '''
                INSERT INTO permissions (user_id, source_id, can_search)
                VALUES (%s, %s, TRUE)
            ''', (user_id, source_id))
            new_status = True
            
        status_text = "فعال" if new_status else "غیرفعال"
        bot.answer_callback_query(call.id, f"✅ دسترسی کاربر {status_text} شد.")
        
        # Show updated source permissions
        self.show_source_permissions(call.message, source_id)
        
    def start_contact_admin(self, message):
        """Start contact admin flow"""
        bot = telebot.TeleBot.__self__
        user_id = message.from_user.id
        
        # Store user in contact state
        self.contact_states[user_id] = {
            'step': 'waiting_for_message'
        }
        
        bot.send_message(
            message.chat.id,
            "📞 ارتباط با مدیر:\n\n"
            "لطفاً پیام خود را برای مدیر ارسال کنید:"
        )
        bot.register_next_step_handler(message, self.process_contact_message)
        
    def process_contact_message(self, message):
        """Process contact admin message"""
        bot = telebot.TeleBot.__self__
        user_id = message.from_user.id
        
        # Get admin chat ID from config
        admin_chat_id = self.config.get_config('admin_chat_id')
        
        if not admin_chat_id:
            # Get first admin from database
            admin = self.db.fetch_one('telegram_archive_bot', '''
                SELECT user_id FROM users WHERE is_admin = TRUE LIMIT 1
            ''')
            
            if admin:
                admin_chat_id = admin['user_id']
            else:
                bot.send_message(
                    message.chat.id,
                    "❌ متأسفانه امکان ارتباط با مدیر در حال حاضر وجود ندارد."
                )
                return
                
        # Get user info
        user = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM users WHERE user_id = %s
        ''', (user_id,))
        
        username = user['username'] if user else f"کاربر {user_id}"
        
        # Forward message to admin
        try:
            bot.send_message(
                admin_chat_id,
                f"📨 پیام جدید از {username} ({user_id}):\n\n{message.text}"
            )
            
            bot.send_message(
                message.chat.id,
                "✅ پیام شما با موفقیت به مدیر ارسال شد.\n"
                "مدیر در اسرع وقت به شما پاسخ خواهد داد."
            )
        except Exception as e:
            logger.error(f"Error forwarding message to admin: {e}")
            bot.send_message(
                message.chat.id,
                "❌ متأسفانه خطایی در ارسال پیام رخ داد. لطفاً بعداً دوباره تلاش کنید."
            )
            
        # Clear contact state
        if user_id in self.contact_states:
            del self.contact_states[user_id]
            
    def get_source_type_persian(self, source_type):
        """Convert source type to Persian"""
        types = {
            'channel': 'کانال',
            'group': 'گروه معمولی',
            'supergroup': 'سوپرگروه',
            'topic_group': 'گروه با موضوعات'
        }
        return types.get(source_type, source_type)

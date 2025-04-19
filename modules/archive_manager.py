
import telebot
from telebot import types
import json
import logging

logger = logging.getLogger(__name__)

class ArchiveManager:
    """Manager for handling archiving operations"""
    
    def __init__(self, bot, db_manager, config_manager):
        self.bot = bot
        self.db = db_manager
        self.config = config_manager
        self.user_states = {}  # Store user states during setup flow
        
    def start_archive_setup(self, message):
        """Start the archive setup flow"""
        user_id = message.from_user.id
        
        # Initialize user state
        self.user_states[user_id] = {
            'step': 'request_source_type',
            'source_data': {}
        }
        
        # Create source type selection keyboard
        markup = types.InlineKeyboardMarkup(row_width=2)
        channel_btn = types.InlineKeyboardButton("📢 کانال", callback_data="archive_source_channel")
        group_btn = types.InlineKeyboardButton("👥 گروه معمولی", callback_data="archive_source_group")
        supergroup_btn = types.InlineKeyboardButton("👥 سوپرگروه", callback_data="archive_source_supergroup")
        topic_group_btn = types.InlineKeyboardButton("📋 گروه با موضوعات", callback_data="archive_source_topic_group")
        markup.add(channel_btn, group_btn, supergroup_btn, topic_group_btn)
        
        self.bot.send_message(
            message.chat.id,
            "📦 تنظیم آرشیو جدید:\n\n"
            "لطفاً نوع منبع را انتخاب کنید:",
            reply_markup=markup
        )
        
    def handle_callback(self, call):
        """Handle callback queries for archive setup"""
        data = call.data
        user_id = call.from_user.id
        
        # Ensure user state exists
        if user_id not in self.user_states and not data.startswith("archive_view_"):
            self.bot.answer_callback_query(call.id, "خطا: لطفاً دوباره از ابتدا شروع کنید.")
            return
            
        # Handle different callback patterns
        if data.startswith("archive_source_"):
            self.handle_source_type_selection(call)
            
        elif data.startswith("archive_filter_"):
            self.handle_filter_selection(call)
            
        elif data.startswith("archive_topic_"):
            self.handle_topic_selection(call)
            
        elif data == "archive_save_settings":
            self.save_archive_settings(call)
            
        elif data.startswith("archive_view_"):
            # View archived source details
            source_id = int(data.split("_")[-1])
            self.show_source_details(call.message, source_id)
            
        elif data.startswith("archive_toggle_"):
            # Toggle source active status
            source_id = int(data.split("_")[-1])
            self.toggle_source_status(call, source_id)
            
        elif data.startswith("archive_delete_"):
            # Delete source
            source_id = int(data.split("_")[-1])
            self.delete_source(call, source_id)
            
        elif data.startswith("archive_edit_"):
            # Edit source settings
            source_id = int(data.split("_")[-1])
            self.edit_source_settings(call, source_id)
            
    def handle_source_type_selection(self, call):
        """Handle source type selection"""
        user_id = call.from_user.id
        data = call.data
        source_type = data.split("_")[-1]
        
        # Update user state
        self.user_states[user_id]['source_data']['type'] = source_type
        self.user_states[user_id]['step'] = 'request_source_link'
        
        # Ask for channel/group link or ID
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔗 لطفاً لینک یا شناسه عددی منبع را وارد کنید:\n"
                 "مثال: https://t.me/channel_name یا @channel_name یا -1001234567890",
        )
        
        # Register next step handler
        self.bot.register_next_step_handler(call.message, self.process_source_link)
        
    def process_source_link(self, message):
        """Process source link input"""
        user_id = message.from_user.id
        link = message.text.strip()
        
        # Validate link format
        if link.startswith('https://t.me/'):
            username = link.split('/')[-1]
            self.user_states[user_id]['source_data']['chat_username'] = username
        elif link.startswith('@'):
            username = link[1:]
            self.user_states[user_id]['source_data']['chat_username'] = username
        elif link.startswith('-100') and link[4:].isdigit():
            chat_id = int(link)
            self.user_states[user_id]['source_data']['chat_id'] = chat_id
        else:
            self.bot.send_message(
                message.chat.id,
                "❌ فرمت لینک یا شناسه نامعتبر است. لطفاً دوباره تلاش کنید."
            )
            self.bot.register_next_step_handler(message, self.process_source_link)
            return
            
        # Ask for channel/group title
        self.user_states[user_id]['step'] = 'request_source_title'
        self.bot.send_message(
            message.chat.id,
            "📝 لطفاً عنوان دلخواه برای این منبع را وارد کنید:"
        )
        self.bot.register_next_step_handler(message, self.process_source_title)
        
    def process_source_title(self, message):
        """Process source title input"""
        user_id = message.from_user.id
        title = message.text.strip()
        
        # Validate title
        if len(title) < 3 or len(title) > 100:
            self.bot.send_message(
                message.chat.id,
                "❌ عنوان باید بین 3 تا 100 کاراکتر باشد. لطفاً دوباره تلاش کنید."
            )
            self.bot.register_next_step_handler(message, self.process_source_title)
            return
            
        # Update user state
        self.user_states[user_id]['source_data']['chat_title'] = title
        
        # Check if source type is topic_group
        if self.user_states[user_id]['source_data']['type'] == 'topic_group':
            self.user_states[user_id]['step'] = 'request_topics'
            self.bot.send_message(
                message.chat.id,
                "📋 لطفاً شناسه‌های موضوعات (Topic IDs) را وارد کنید:\n"
                "مقادیر را با کاما جدا کنید یا 'all' برای همه موضوعات.\n"
                "مثال: 1,2,5,10 یا all"
            )
            self.bot.register_next_step_handler(message, self.process_topics)
        else:
            # Show filter options
            self.show_filter_options(message)
            
    def process_topics(self, message):
        """Process topic IDs input"""
        user_id = message.from_user.id
        topics_input = message.text.strip().lower()
        
        if topics_input == 'all':
            topics = ['all']
        else:
            # Validate and parse topic IDs
            try:
                topics = [int(tid.strip()) for tid in topics_input.split(',') if tid.strip().isdigit()]
                if not topics:
                    raise ValueError("No valid topic IDs")
            except Exception:
                self.bot.send_message(
                    message.chat.id,
                    "❌ فرمت شناسه‌های موضوعات نامعتبر است. لطفاً دوباره تلاش کنید."
                )
                self.bot.register_next_step_handler(message, self.process_topics)
                return
                
        # Update user state
        self.user_states[user_id]['source_data']['topics'] = topics
        
        # Show filter options
        self.show_filter_options(message)
        
    def show_filter_options(self, message):
        """Show message filter options"""
        user_id = message.from_user.id
        
        # Update user state
        self.user_states[user_id]['step'] = 'select_filters'
        
        # Initialize filter config if not exists
        if 'filter_config' not in self.user_states[user_id]['source_data']:
            self.user_states[user_id]['source_data']['filter_config'] = {
                'text': True,
                'photo': True,
                'video': True,
                'document': True,
                'audio': True,
                'voice': True,
                'sticker': True,
                'animation': True,
                'keywords': []
            }
        
        # Create filter selection keyboard
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        filter_config = self.user_states[user_id]['source_data']['filter_config']
        
        # Media type filters
        text_status = "✅" if filter_config['text'] else "❌"
        photo_status = "✅" if filter_config['photo'] else "❌"
        video_status = "✅" if filter_config['video'] else "❌"
        document_status = "✅" if filter_config['document'] else "❌"
        audio_status = "✅" if filter_config['audio'] else "❌"
        voice_status = "✅" if filter_config['voice'] else "❌"
        sticker_status = "✅" if filter_config['sticker'] else "❌"
        animation_status = "✅" if filter_config['animation'] else "❌"
        
        text_btn = types.InlineKeyboardButton(f"متن {text_status}", callback_data="archive_filter_text")
        photo_btn = types.InlineKeyboardButton(f"عکس {photo_status}", callback_data="archive_filter_photo")
        video_btn = types.InlineKeyboardButton(f"ویدیو {video_status}", callback_data="archive_filter_video")
        doc_btn = types.InlineKeyboardButton(f"فایل {document_status}", callback_data="archive_filter_document")
        audio_btn = types.InlineKeyboardButton(f"صوت {audio_status}", callback_data="archive_filter_audio")
        voice_btn = types.InlineKeyboardButton(f"ویس {voice_status}", callback_data="archive_filter_voice")
        sticker_btn = types.InlineKeyboardButton(f"استیکر {sticker_status}", callback_data="archive_filter_sticker")
        anim_btn = types.InlineKeyboardButton(f"گیف {animation_status}", callback_data="archive_filter_animation")
        
        # Keyword filter button
        keyword_btn = types.InlineKeyboardButton("🔤 فیلتر کلمات کلیدی", callback_data="archive_filter_keywords")
        
        # Save button
        save_btn = types.InlineKeyboardButton("💾 ذخیره تنظیمات", callback_data="archive_save_settings")
        
        # Add buttons to markup
        markup.add(text_btn, photo_btn, video_btn, doc_btn, audio_btn, voice_btn, sticker_btn, anim_btn, keyword_btn, save_btn)
        
        self.bot.send_message(
            message.chat.id,
            "🔍 فیلترهای پیام:\n\n"
            "نوع پیام‌هایی که می‌خواهید آرشیو شوند را انتخاب کنید:",
            reply_markup=markup
        )
        
    def handle_filter_selection(self, call):
        """Handle filter selection callbacks"""
        user_id = call.from_user.id
        data = call.data
        filter_type = data.split("_")[-1]
        
        # Toggle filter status
        if filter_type in ['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation']:
            current_value = self.user_states[user_id]['source_data']['filter_config'][filter_type]
            self.user_states[user_id]['source_data']['filter_config'][filter_type] = not current_value
            
            # Update keyboard
            self.update_filter_keyboard(call.message, user_id)
            
        elif filter_type == 'keywords':
            # Ask for keywords
            self.bot.answer_callback_query(call.id, "لطفاً کلمات کلیدی را وارد کنید.")
            self.bot.send_message(
                call.message.chat.id,
                "🔤 فیلتر کلمات کلیدی:\n\n"
                "کلمات کلیدی را با کاما جدا کنید. پیام‌ها فقط در صورت داشتن این کلمات آرشیو می‌شوند.\n"
                "برای حذف فیلتر کلمات کلیدی، عبارت 'clear' را وارد کنید."
            )
            self.bot.register_next_step_handler(call.message, self.process_keywords)
            
    def process_keywords(self, message):
        """Process keywords input"""
        user_id = message.from_user.id
        keywords_input = message.text.strip()
        
        if keywords_input.lower() == 'clear':
            # Clear keywords
            self.user_states[user_id]['source_data']['filter_config']['keywords'] = []
            self.bot.send_message(
                message.chat.id,
                "✅ فیلتر کلمات کلیدی حذف شد."
            )
        else:
            # Parse keywords
            keywords = [k.strip() for k in keywords_input.split(',') if k.strip()]
            self.user_states[user_id]['source_data']['filter_config']['keywords'] = keywords
            self.bot.send_message(
                message.chat.id,
                f"✅ {len(keywords)} کلمه کلیدی ثبت شد."
            )
            
        # Show updated filter options
        self.show_filter_options(message)
        
    def update_filter_keyboard(self, message, user_id):
        """Update filter keyboard with current settings"""
        filter_config = self.user_states[user_id]['source_data']['filter_config']
        
        # Create updated filter selection keyboard
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Media type filters with updated status
        text_status = "✅" if filter_config['text'] else "❌"
        photo_status = "✅" if filter_config['photo'] else "❌"
        video_status = "✅" if filter_config['video'] else "❌"
        document_status = "✅" if filter_config['document'] else "❌"
        audio_status = "✅" if filter_config['audio'] else "❌"
        voice_status = "✅" if filter_config['voice'] else "❌"
        sticker_status = "✅" if filter_config['sticker'] else "❌"
        animation_status = "✅" if filter_config['animation'] else "❌"
        
        text_btn = types.InlineKeyboardButton(f"متن {text_status}", callback_data="archive_filter_text")
        photo_btn = types.InlineKeyboardButton(f"عکس {photo_status}", callback_data="archive_filter_photo")
        video_btn = types.InlineKeyboardButton(f"ویدیو {video_status}", callback_data="archive_filter_video")
        doc_btn = types.InlineKeyboardButton(f"فایل {document_status}", callback_data="archive_filter_document")
        audio_btn = types.InlineKeyboardButton(f"صوت {audio_status}", callback_data="archive_filter_audio")
        voice_btn = types.InlineKeyboardButton(f"ویس {voice_status}", callback_data="archive_filter_voice")
        sticker_btn = types.InlineKeyboardButton(f"استیکر {sticker_status}", callback_data="archive_filter_sticker")
        anim_btn = types.InlineKeyboardButton(f"گیف {animation_status}", callback_data="archive_filter_animation")
        
        # Keyword filter button
        keyword_count = len(filter_config['keywords'])
        keyword_text = f"🔤 فیلتر کلمات کلیدی ({keyword_count})"
        keyword_btn = types.InlineKeyboardButton(keyword_text, callback_data="archive_filter_keywords")
        
        # Save button
        save_btn = types.InlineKeyboardButton("💾 ذخیره تنظیمات", callback_data="archive_save_settings")
        
        # Add buttons to markup
        markup.add(text_btn, photo_btn, video_btn, doc_btn, audio_btn, voice_btn, sticker_btn, anim_btn, keyword_btn, save_btn)
        
        self.bot.edit_message_reply_markup(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reply_markup=markup
        )
        
    def save_archive_settings(self, call):
        """Save archive settings to database"""
        user_id = call.from_user.id
        source_data = self.user_states[user_id]['source_data']
        
        # Prepare data for database
        chat_id = source_data.get('chat_id')
        chat_username = source_data.get('chat_username', '')
        chat_title = source_data['chat_title']
        source_type = source_data['type']
        filter_config = json.dumps(source_data['filter_config'])
        
        # Prepare topics config if applicable
        topics_config = 'null'
        if source_type == 'topic_group' and 'topics' in source_data:
            topics_config = json.dumps(source_data['topics'])
        
        # Insert into database
        cursor = self.db.execute_query('telegram_archive_bot', '''
            INSERT INTO sources 
            (type, chat_id, chat_title, chat_username, filter_config, topics_config, added_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (source_type, chat_id, chat_title, chat_username, filter_config, topics_config, user_id))
        
        # Get the inserted ID
        if cursor:
            source_id = cursor.lastrowid
            
            # Clear user state
            del self.user_states[user_id]
            
            self.bot.answer_callback_query(call.id, "✅ تنظیمات آرشیو با موفقیت ذخیره شد.")
            
            # Show success message
            self.bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ آرشیو جدید با موفقیت اضافه شد!\n\n"
                     f"🔸 نوع: {self.get_source_type_persian(source_type)}\n"
                     f"🔸 عنوان: {chat_title}\n\n"
                     f"برای مشاهده جزئیات و ویرایش، به بخش جستجو در آرشیو مراجعه کنید."
            )
        else:
            self.bot.answer_callback_query(call.id, "❌ خطا در ذخیره تنظیمات. لطفاً دوباره تلاش کنید.")
    
    def show_source_details(self, message, source_id):
        """Show details of an archived source"""
        # Get source details from database
        source = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM sources WHERE id = %s
        ''', (source_id,))
        
        if not source:
            self.bot.send_message(
                message.chat.id,
                "❌ منبع مورد نظر یافت نشد."
            )
            return
            
        # Parse JSON fields
        filter_config = json.loads(source['filter_config'])
        topics_config = json.loads(source['topics_config']) if source['topics_config'] else None
        
        # Create status text
        status_text = "🟢 فعال" if source['is_active'] else "🔴 غیرفعال"
        
        # Create message text
        text = f"📦 جزئیات منبع آرشیو:\n\n"
        text += f"🔸 شناسه: {source['id']}\n"
        text += f"🔸 نوع: {self.get_source_type_persian(source['type'])}\n"
        text += f"🔸 عنوان: {source['chat_title']}\n"
        text += f"🔸 وضعیت: {status_text}\n\n"
        
        # Add username/chat_id info
        if source['chat_username']:
            text += f"🔹 نام کاربری: @{source['chat_username']}\n"
        if source['chat_id']:
            text += f"🔹 شناسه چت: {source['chat_id']}\n\n"
            
        # Add filter info
        text += "🔍 فیلترها:\n"
        for filter_type, enabled in filter_config.items():
            if filter_type == 'keywords':
                keyword_count = len(filter_config['keywords'])
                if keyword_count > 0:
                    text += f"  • کلمات کلیدی: {', '.join(filter_config['keywords'])}\n"
            else:
                status = "✅" if enabled else "❌"
                text += f"  • {self.get_filter_type_persian(filter_type)}: {status}\n"
                
        # Add topics info if applicable
        if topics_config:
            text += "\n📋 موضوعات:\n"
            if 'all' in topics_config:
                text += "  • همه موضوعات\n"
            else:
                text += f"  • موضوعات: {', '.join(map(str, topics_config))}\n"
                
        # Create inline keyboard for actions
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Toggle status button
        toggle_text = "🔴 غیرفعال کردن" if source['is_active'] else "🟢 فعال کردن"
        toggle_btn = types.InlineKeyboardButton(toggle_text, callback_data=f"archive_toggle_{source_id}")
        
        # Edit button
        edit_btn = types.InlineKeyboardButton("✏️ ویرایش", callback_data=f"archive_edit_{source_id}")
        
        # Delete button
        delete_btn = types.InlineKeyboardButton("🗑️ حذف", callback_data=f"archive_delete_{source_id}")
        
        # Add buttons to markup
        markup.add(toggle_btn, edit_btn, delete_btn)
        
        self.bot.send_message(
            message.chat.id,
            text,
            reply_markup=markup
        )
        
    def toggle_source_status(self, call, source_id):
        """Toggle source active status"""
        # Get current status
        source = self.db.fetch_one('telegram_archive_bot', '''
            SELECT is_active FROM sources WHERE id = %s
        ''', (source_id,))
        
        if not source:
            self.bot.answer_callback_query(call.id, "❌ منبع مورد نظر یافت نشد.")
            return
            
        # Toggle status
        new_status = not source['is_active']
        self.db.execute_query('telegram_archive_bot', '''
            UPDATE sources SET is_active = %s WHERE id = %s
        ''', (new_status, source_id))
        
        status_text = "فعال" if new_status else "غیرفعال"
        self.bot.answer_callback_query(call.id, f"✅ وضعیت منبع به {status_text} تغییر کرد.")
        
        # Show updated source details
        self.show_source_details(call.message, source_id)
        
    def delete_source(self, call, source_id):
        """Delete source from database"""
        # Confirm deletion with a new message
        markup = types.InlineKeyboardMarkup(row_width=2)
        confirm_btn = types.InlineKeyboardButton("✅ بله، حذف شود", callback_data=f"archive_delete_confirm_{source_id}")
        cancel_btn = types.InlineKeyboardButton("❌ خیر، انصراف", callback_data=f"archive_view_{source_id}")
        markup.add(confirm_btn, cancel_btn)
        
        self.bot.send_message(
            call.message.chat.id,
            "⚠️ آیا از حذف این منبع آرشیو اطمینان دارید؟\n"
            "این عمل غیرقابل بازگشت است و تمام پیام‌های آرشیو شده از این منبع حذف خواهند شد.",
            reply_markup=markup
        )
        
    def edit_source_settings(self, call, source_id):
        """Edit source settings"""
        user_id = call.from_user.id
        
        # Get source details from database
        source = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM sources WHERE id = %s
        ''', (source_id,))
        
        if not source:
            self.bot.answer_callback_query(call.id, "❌ منبع مورد نظر یافت نشد.")
            return
            
        # Initialize user state with current settings
        self.user_states[user_id] = {
            'step': 'edit_source',
            'source_id': source_id,
            'source_data': {
                'type': source['type'],
                'chat_id': source['chat_id'],
                'chat_username': source['chat_username'],
                'chat_title': source['chat_title'],
                'filter_config': json.loads(source['filter_config']),
            }
        }
        
        # Add topics if applicable
        if source['topics_config']:
            self.user_states[user_id]['source_data']['topics'] = json.loads(source['topics_config'])
            
        # Show filter options for editing
        self.show_filter_options(call.message)
        
    def get_source_type_persian(self, source_type):
        """Convert source type to Persian"""
        types = {
            'channel': 'کانال',
            'group': 'گروه معمولی',
            'supergroup': 'سوپرگروه',
            'topic_group': 'گروه با موضوعات'
        }
        return types.get(source_type, source_type)
        
    def get_filter_type_persian(self, filter_type):
        """Convert filter type to Persian"""
        types = {
            'text': 'متن',
            'photo': 'عکس',
            'video': 'ویدیو',
            'document': 'فایل',
            'audio': 'صوت',
            'voice': 'ویس',
            'sticker': 'استیکر',
            'animation': 'گیف'
        }
        return types.get(filter_type, filter_type)

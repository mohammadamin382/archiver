
import telebot
from telebot import types
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SearchManager:
    """Manager for searching in archived messages"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.user_states = {}  # Store user search states
        
    def start_search(self, message):
        """Start the search flow"""
        user_id = message.from_user.id
        
        # Initialize user search state
        self.user_states[user_id] = {
            'step': 'select_source',
            'filters': {}
        }
        
        # Get sources for this user
        sources = self.get_accessible_sources(user_id)
        
        if not sources:
            self.bot.send_message(
                message.chat.id,
                "❌ هیچ منبع آرشیوی برای شما قابل دسترس نیست."
            )
            return
            
        # Create inline keyboard for source selection
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for source in sources:
            source_text = f"{source['chat_title']} ({self.get_source_type_persian(source['type'])})"
            source_btn = types.InlineKeyboardButton(source_text, callback_data=f"search_source_{source['id']}")
            markup.add(source_btn)
            
        self.bot.send_message(
            message.chat.id,
            "🔍 جستجو در آرشیو:\n\n"
            "لطفاً منبع مورد نظر برای جستجو را انتخاب کنید:",
            reply_markup=markup
        )
        
    def handle_callback(self, call):
        """Handle callback queries for search flow"""
        bot = telebot.TeleBot.__self__
        data = call.data
        user_id = call.from_user.id
        
        # Ensure user state exists
        if user_id not in self.user_states and not data.startswith("search_result_"):
            bot.answer_callback_query(call.id, "خطا: لطفاً دوباره از ابتدا شروع کنید.")
            return
            
        # Handle different callback patterns
        if data.startswith("search_source_"):
            # Source selection
            source_id = int(data.split("_")[-1])
            self.select_source(call, source_id)
            
        elif data.startswith("search_filter_"):
            # Filter selection
            filter_type = data.split("_")[-1]
            self.select_filter(call, filter_type)
            
        elif data == "search_execute":
            # Execute search
            self.execute_search(call)
            
        elif data.startswith("search_result_"):
            # View search result
            result_id = int(data.split("_")[-1])
            self.show_result_details(call, result_id)
            
        elif data.startswith("search_page_"):
            # Pagination
            page = int(data.split("_")[-1])
            self.show_search_results(call.message, user_id, page)
            
        elif data == "search_export":
            # Export search results
            self.export_search_results(call)
            
        elif data == "search_new":
            # Start new search
            self.start_search(call.message)
            
    def select_source(self, call, source_id):
        """Select a source for searching"""
        bot = telebot.TeleBot.__self__
        user_id = call.from_user.id
        
        # Update user state
        self.user_states[user_id]['source_id'] = source_id
        self.user_states[user_id]['step'] = 'select_filters'
        
        # Get source details
        source = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM sources WHERE id = %s
        ''', (source_id,))
        
        if not source:
            bot.answer_callback_query(call.id, "❌ منبع مورد نظر یافت نشد.")
            return
            
        # Show search filters
        self.show_search_filters(call.message, user_id, source)
        
    def show_search_filters(self, message, user_id, source):
        """Show search filters for the selected source"""
        bot = telebot.TeleBot.__self__
        
        # Create inline keyboard for filters
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Get current filters
        filters = self.user_states[user_id].get('filters', {})
        
        # Text search button
        text_btn = types.InlineKeyboardButton("🔤 جستجوی متن", callback_data="search_filter_text")
        
        # Date range button
        date_btn = types.InlineKeyboardButton("📅 محدوده زمانی", callback_data="search_filter_date")
        
        # Media type button
        media_btn = types.InlineKeyboardButton("📁 نوع رسانه", callback_data="search_filter_media")
        
        # Sender button
        sender_btn = types.InlineKeyboardButton("👤 فرستنده", callback_data="search_filter_sender")
        
        # Topic button (only for topic groups)
        if source['type'] == 'topic_group' and source['topics_config']:
            topic_btn = types.InlineKeyboardButton("📋 موضوع", callback_data="search_filter_topic")
            markup.add(topic_btn)
            
        # Search button
        search_btn = types.InlineKeyboardButton("🔍 جستجو", callback_data="search_execute")
        
        # Add buttons to markup
        markup.add(text_btn, date_btn, media_btn, sender_btn, search_btn)
        
        # Create filters summary text
        filter_text = "🔍 فیلترهای جستجو:\n\n"
        
        if 'text' in filters and filters['text']:
            filter_text += f"🔤 متن: {filters['text']}\n"
            
        if 'date_from' in filters or 'date_to' in filters:
            date_from = filters.get('date_from', 'ابتدا')
            date_to = filters.get('date_to', 'انتها')
            filter_text += f"📅 زمان: از {date_from} تا {date_to}\n"
            
        if 'media_type' in filters:
            media_type = self.get_media_type_persian(filters['media_type'])
            filter_text += f"📁 نوع رسانه: {media_type}\n"
            
        if 'sender_id' in filters or 'sender_name' in filters:
            sender = filters.get('sender_name', filters.get('sender_id', ''))
            filter_text += f"👤 فرستنده: {sender}\n"
            
        if 'topic_id' in filters:
            topic_id = filters['topic_id']
            filter_text += f"📋 موضوع: {topic_id}\n"
            
        if not any(k in filters for k in ['text', 'date_from', 'date_to', 'media_type', 'sender_id', 'sender_name', 'topic_id']):
            filter_text += "هیچ فیلتری انتخاب نشده است. تمام پیام‌ها نمایش داده خواهند شد.\n"
            
        bot.send_message(
            message.chat.id,
            f"🔍 جستجو در آرشیو:\n\n"
            f"منبع: {source['chat_title']}\n\n"
            f"{filter_text}\n"
            f"برای اضافه کردن فیلتر یا انجام جستجو، گزینه‌های زیر را انتخاب کنید:",
            reply_markup=markup
        )
        
    def select_filter(self, call, filter_type):
        """Handle filter selection"""
        bot = telebot.TeleBot.__self__
        user_id = call.from_user.id
        
        if filter_type == 'text':
            # Ask for text search
            bot.answer_callback_query(call.id, "لطفاً متن مورد جستجو را وارد کنید.")
            bot.send_message(
                call.message.chat.id,
                "🔤 جستجوی متن:\n\n"
                "لطفاً کلمه یا عبارت مورد نظر برای جستجو را وارد کنید:"
            )
            bot.register_next_step_handler(call.message, self.process_text_filter)
            
        elif filter_type == 'date':
            # Show date range options
            self.show_date_filter_options(call.message)
            
        elif filter_type == 'media':
            # Show media type options
            self.show_media_filter_options(call.message)
            
        elif filter_type == 'sender':
            # Ask for sender ID or name
            bot.answer_callback_query(call.id, "لطفاً شناسه یا نام فرستنده را وارد کنید.")
            bot.send_message(
                call.message.chat.id,
                "👤 فیلتر فرستنده:\n\n"
                "لطفاً شناسه یا نام فرستنده را وارد کنید:"
            )
            bot.register_next_step_handler(call.message, self.process_sender_filter)
            
        elif filter_type == 'topic':
            # Get source ID from user state
            source_id = self.user_states[user_id]['source_id']
            
            # Get topics for this source
            source = self.db.fetch_one('telegram_archive_bot', '''
                SELECT topics_config FROM sources WHERE id = %s
            ''', (source_id,))
            
            if source and source['topics_config']:
                topics = json.loads(source['topics_config'])
                self.show_topic_filter_options(call.message, topics)
            else:
                bot.answer_callback_query(call.id, "❌ موضوعی برای این منبع تعریف نشده است.")
                
    def process_text_filter(self, message):
        """Process text search input"""
        bot = telebot.TeleBot.__self__
        user_id = message.from_user.id
        text = message.text.strip()
        
        if len(text) < 2:
            bot.send_message(
                message.chat.id,
                "❌ متن جستجو باید حداقل 2 کاراکتر باشد. لطفاً دوباره تلاش کنید."
            )
            bot.register_next_step_handler(message, self.process_text_filter)
            return
            
        # Update user state
        self.user_states[user_id]['filters']['text'] = text
        
        # Get source details
        source_id = self.user_states[user_id]['source_id']
        source = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM sources WHERE id = %s
        ''', (source_id,))
        
        # Show updated filters
        self.show_search_filters(message, user_id, source)
        
    def show_date_filter_options(self, message):
        """Show date range filter options"""
        bot = telebot.TeleBot.__self__
        
        # Create inline keyboard for date range options
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Predefined date ranges
        today_btn = types.InlineKeyboardButton("امروز", callback_data="search_date_today")
        yesterday_btn = types.InlineKeyboardButton("دیروز", callback_data="search_date_yesterday")
        week_btn = types.InlineKeyboardButton("هفته اخیر", callback_data="search_date_week")
        month_btn = types.InlineKeyboardButton("ماه اخیر", callback_data="search_date_month")
        custom_btn = types.InlineKeyboardButton("محدوده سفارشی", callback_data="search_date_custom")
        
        # Add buttons to markup
        markup.add(today_btn, yesterday_btn, week_btn, month_btn, custom_btn)
        
        bot.send_message(
            message.chat.id,
            "📅 فیلتر محدوده زمانی:\n\n"
            "لطفاً محدوده زمانی مورد نظر را انتخاب کنید:",
            reply_markup=markup
        )
        
    def show_media_filter_options(self, message):
        """Show media type filter options"""
        bot = telebot.TeleBot.__self__
        
        # Create inline keyboard for media types
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # Media type buttons
        text_btn = types.InlineKeyboardButton("متن", callback_data="search_media_text")
        photo_btn = types.InlineKeyboardButton("عکس", callback_data="search_media_photo")
        video_btn = types.InlineKeyboardButton("ویدیو", callback_data="search_media_video")
        doc_btn = types.InlineKeyboardButton("فایل", callback_data="search_media_document")
        audio_btn = types.InlineKeyboardButton("صوت", callback_data="search_media_audio")
        voice_btn = types.InlineKeyboardButton("ویس", callback_data="search_media_voice")
        sticker_btn = types.InlineKeyboardButton("استیکر", callback_data="search_media_sticker")
        anim_btn = types.InlineKeyboardButton("گیف", callback_data="search_media_animation")
        
        # Add buttons to markup
        markup.add(text_btn, photo_btn, video_btn, doc_btn, audio_btn, voice_btn, sticker_btn, anim_btn)
        
        bot.send_message(
            message.chat.id,
            "📁 فیلتر نوع رسانه:\n\n"
            "لطفاً نوع رسانه مورد نظر را انتخاب کنید:",
            reply_markup=markup
        )
        
    def process_sender_filter(self, message):
        """Process sender filter input"""
        bot = telebot.TeleBot.__self__
        user_id = message.from_user.id
        sender = message.text.strip()
        
        # Try to parse as user ID
        if sender.isdigit():
            self.user_states[user_id]['filters']['sender_id'] = int(sender)
        else:
            self.user_states[user_id]['filters']['sender_name'] = sender
            
        # Get source details
        source_id = self.user_states[user_id]['source_id']
        source = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM sources WHERE id = %s
        ''', (source_id,))
        
        # Show updated filters
        self.show_search_filters(message, user_id, source)
        
    def show_topic_filter_options(self, message, topics):
        """Show topic filter options"""
        bot = telebot.TeleBot.__self__
        
        # Create inline keyboard for topics
        markup = types.InlineKeyboardMarkup(row_width=2)
        
        # All topics button
        all_btn = types.InlineKeyboardButton("همه موضوعات", callback_data="search_topic_all")
        markup.add(all_btn)
        
        # Individual topic buttons
        if 'all' not in topics:
            for topic_id in topics:
                topic_btn = types.InlineKeyboardButton(f"موضوع {topic_id}", callback_data=f"search_topic_{topic_id}")
                markup.add(topic_btn)
        
        bot.send_message(
            message.chat.id,
            "📋 فیلتر موضوع:\n\n"
            "لطفاً موضوع مورد نظر را انتخاب کنید:",
            reply_markup=markup
        )
        
    def execute_search(self, call):
        """Execute search with selected filters"""
        bot = telebot.TeleBot.__self__
        user_id = call.from_user.id
        
        if user_id not in self.user_states:
            bot.answer_callback_query(call.id, "❌ خطا در جستجو. لطفاً دوباره از ابتدا شروع کنید.")
            return
            
        # Get source ID and filters
        source_id = self.user_states[user_id]['source_id']
        filters = self.user_states[user_id]['filters']
        
        # Show loading message
        bot.answer_callback_query(call.id, "در حال جستجو...")
        processing_msg = bot.send_message(
            call.message.chat.id,
            "🔄 در حال پردازش جستجو... لطفاً منتظر بمانید."
        )
        
        # Store search results in user state
        self.user_states[user_id]['results'] = self.search_messages(source_id, filters)
        self.user_states[user_id]['page'] = 1
        
        # Delete processing message
        bot.delete_message(
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )
        
        # Show search results
        self.show_search_results(call.message, user_id)
        
    def search_messages(self, source_id, filters):
        """Search messages based on filters"""
        # Build SQL query
        query = '''
            SELECT * FROM archived_messages 
            WHERE source_id = %s
        '''
        params = [source_id]
        
        # Add text filter
        if 'text' in filters and filters['text']:
            query += " AND message_text LIKE %s"
            params.append(f"%{filters['text']}%")
            
        # Add date range filter
        if 'date_from' in filters and filters['date_from']:
            query += " AND message_date >= %s"
            params.append(filters['date_from'])
            
        if 'date_to' in filters and filters['date_to']:
            query += " AND message_date <= %s"
            params.append(filters['date_to'])
            
        # Add media type filter
        if 'media_type' in filters and filters['media_type']:
            query += " AND media_type = %s"
            params.append(filters['media_type'])
            
        # Add sender filter
        if 'sender_id' in filters and filters['sender_id']:
            query += " AND sender_id = %s"
            params.append(filters['sender_id'])
        elif 'sender_name' in filters and filters['sender_name']:
            query += " AND sender_name LIKE %s"
            params.append(f"%{filters['sender_name']}%")
            
        # Add topic filter
        if 'topic_id' in filters and filters['topic_id'] != 'all':
            query += " AND topic_id = %s"
            params.append(filters['topic_id'])
            
        # Add order by
        query += " ORDER BY message_date DESC"
        
        # Execute query
        return self.db.fetch_all('telegram_archive_bot', query, params)
        
    def show_search_results(self, message, user_id, page=1):
        """Show search results"""
        bot = telebot.TeleBot.__self__
        
        # Get results from user state
        results = self.user_states[user_id].get('results', [])
        
        if not results:
            bot.send_message(
                message.chat.id,
                "❌ هیچ نتیجه‌ای برای جستجوی شما یافت نشد."
            )
            return
            
        # Pagination
        page_size = 10
        total_pages = (len(results) + page_size - 1) // page_size
        
        # Ensure page is valid
        page = max(1, min(page, total_pages))
        self.user_states[user_id]['page'] = page
        
        # Get current page items
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, len(results))
        page_results = results[start_idx:end_idx]
        
        # Create results text
        text = f"🔍 نتایج جستجو ({len(results)} مورد یافت شد):\n\n"
        
        for idx, result in enumerate(page_results, start=start_idx + 1):
            # Format date
            date = result['message_date'].strftime('%Y-%m-%d %H:%M')
            
            # Get message preview
            preview = result['message_text'] or self.get_media_type_persian(result['media_type'])
            if preview and len(preview) > 50:
                preview = preview[:47] + "..."
                
            text += f"{idx}. [{date}] {result['sender_name']}: {preview}\n"
            
        text += f"\nصفحه {page} از {total_pages}"
        
        # Create inline keyboard for navigation and actions
        markup = types.InlineKeyboardMarkup(row_width=5)
        
        # Pagination buttons
        first_btn = types.InlineKeyboardButton("« اول", callback_data="search_page_1")
        prev_btn = types.InlineKeyboardButton("< قبلی", callback_data=f"search_page_{page-1}")
        page_btn = types.InlineKeyboardButton(f"{page}/{total_pages}", callback_data="search_page_current")
        next_btn = types.InlineKeyboardButton("بعدی >", callback_data=f"search_page_{page+1}")
        last_btn = types.InlineKeyboardButton("آخر »", callback_data=f"search_page_{total_pages}")
        
        # Add pagination row
        pagination_buttons = []
        if page > 1:
            pagination_buttons.extend([first_btn, prev_btn])
        pagination_buttons.append(page_btn)
        if page < total_pages:
            pagination_buttons.extend([next_btn, last_btn])
        markup.row(*pagination_buttons)
        
        # Result buttons
        for idx, result in enumerate(page_results, start=start_idx + 1):
            result_btn = types.InlineKeyboardButton(f"{idx}", callback_data=f"search_result_{result['id']}")
            markup.add(result_btn)
            
        # Export button
        export_btn = types.InlineKeyboardButton("📤 خروجی گرفتن", callback_data="search_export")
        
        # New search button
        new_search_btn = types.InlineKeyboardButton("🔍 جستجوی جدید", callback_data="search_new")
        
        # Add action buttons
        markup.row(export_btn, new_search_btn)
        
        # Try to edit existing message if possible, otherwise send new
        try:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message.message_id,
                text=text,
                reply_markup=markup
            )
        except Exception:
            bot.send_message(
                message.chat.id,
                text,
                reply_markup=markup
            )
            
    def show_result_details(self, call, result_id):
        """Show details of a search result"""
        bot = telebot.TeleBot.__self__
        
        # Get result from database
        result = self.db.fetch_one('telegram_archive_bot', '''
            SELECT am.*, s.chat_title FROM archived_messages am
            JOIN sources s ON am.source_id = s.id
            WHERE am.id = %s
        ''', (result_id,))
        
        if not result:
            bot.answer_callback_query(call.id, "❌ پیام مورد نظر یافت نشد.")
            return
            
        # Format date
        date = result['message_date'].strftime('%Y-%m-%d %H:%M:%S')
        
        # Create message text
        text = f"📌 جزئیات پیام:\n\n"
        text += f"🔸 منبع: {result['chat_title']}\n"
        text += f"🔸 فرستنده: {result['sender_name']} ({result['sender_id']})\n"
        text += f"🔸 تاریخ: {date}\n"
        text += f"🔸 نوع پیام: {self.get_media_type_persian(result['media_type'])}\n"
        
        if result['topic_id']:
            text += f"🔸 موضوع: {result['topic_id']}\n"
            
        text += f"\n📄 متن پیام:\n{result['message_text'] or '(بدون متن)'}"
        
        # Create back button
        markup = types.InlineKeyboardMarkup(row_width=1)
        back_btn = types.InlineKeyboardButton("🔙 بازگشت به نتایج", callback_data="search_back_to_results")
        markup.add(back_btn)
        
        # If result has media, send media with caption
        has_media = result['media_file_id'] and result['media_type'] != 'text'
        
        if has_media:
            media_type = result['media_type']
            file_id = result['media_file_id']
            
            try:
                if media_type == 'photo':
                    bot.send_photo(call.message.chat.id, file_id, caption=text)
                elif media_type == 'video':
                    bot.send_video(call.message.chat.id, file_id, caption=text)
                elif media_type == 'document':
                    bot.send_document(call.message.chat.id, file_id, caption=text)
                elif media_type == 'audio':
                    bot.send_audio(call.message.chat.id, file_id, caption=text)
                elif media_type == 'voice':
                    bot.send_voice(call.message.chat.id, file_id, caption=text)
                elif media_type == 'sticker':
                    bot.send_sticker(call.message.chat.id, file_id)
                    bot.send_message(call.message.chat.id, text, reply_markup=markup)
                elif media_type == 'animation':
                    bot.send_animation(call.message.chat.id, file_id, caption=text)
                else:
                    bot.send_message(call.message.chat.id, text, reply_markup=markup)
            except Exception as e:
                logger.error(f"Error sending media: {e}")
                bot.send_message(
                    call.message.chat.id,
                    text + "\n\n⚠️ خطا در ارسال رسانه: فایل احتمالاً منقضی شده است.",
                    reply_markup=markup
                )
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
            
    def export_search_results(self, call):
        """Export search results to a file"""
        bot = telebot.TeleBot.__self__
        user_id = call.from_user.id
        
        # Get results from user state
        results = self.user_states[user_id].get('results', [])
        
        if not results:
            bot.answer_callback_query(call.id, "❌ هیچ نتیجه‌ای برای خروجی گرفتن وجود ندارد.")
            return
            
        # Show loading message
        bot.answer_callback_query(call.id, "در حال آماده‌سازی خروجی...")
        processing_msg = bot.send_message(
            call.message.chat.id,
            "🔄 در حال آماده‌سازی خروجی... لطفاً منتظر بمانید."
        )
        
        # Create export text
        export_text = "# نتایج جستجو در آرشیو\n\n"
        
        # Get source details
        source_id = self.user_states[user_id]['source_id']
        source = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM sources WHERE id = %s
        ''', (source_id,))
        
        if source:
            export_text += f"منبع: {source['chat_title']} ({self.get_source_type_persian(source['type'])})\n"
            
        # Add filters
        filters = self.user_states[user_id]['filters']
        
        if filters:
            export_text += "فیلترها:\n"
            
            if 'text' in filters and filters['text']:
                export_text += f"- متن: {filters['text']}\n"
                
            if 'date_from' in filters or 'date_to' in filters:
                date_from = filters.get('date_from', 'ابتدا')
                date_to = filters.get('date_to', 'انتها')
                export_text += f"- زمان: از {date_from} تا {date_to}\n"
                
            if 'media_type' in filters:
                media_type = self.get_media_type_persian(filters['media_type'])
                export_text += f"- نوع رسانه: {media_type}\n"
                
            if 'sender_id' in filters or 'sender_name' in filters:
                sender = filters.get('sender_name', filters.get('sender_id', ''))
                export_text += f"- فرستنده: {sender}\n"
                
            if 'topic_id' in filters:
                topic_id = filters['topic_id']
                export_text += f"- موضوع: {topic_id}\n"
                
        export_text += f"\nتعداد نتایج: {len(results)}\n"
        export_text += f"تاریخ خروجی: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        export_text += "---\n\n"
        
        # Add results
        for idx, result in enumerate(results, start=1):
            date = result['message_date'].strftime('%Y-%m-%d %H:%M:%S')
            
            export_text += f"## {idx}. پیام\n"
            export_text += f"- فرستنده: {result['sender_name']} ({result['sender_id']})\n"
            export_text += f"- تاریخ: {date}\n"
            export_text += f"- نوع پیام: {self.get_media_type_persian(result['media_type'])}\n"
            
            if result['topic_id']:
                export_text += f"- موضوع: {result['topic_id']}\n"
                
            export_text += f"\n{result['message_text'] or '(بدون متن)'}\n\n"
            export_text += "---\n\n"
            
        # Create file
        file_name = f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(export_text)
            
        # Send file
        with open(file_name, 'rb') as f:
            bot.send_document(
                call.message.chat.id,
                f,
                caption="📤 خروجی نتایج جستجو"
            )
            
        # Delete processing message
        bot.delete_message(
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )
        
    def get_accessible_sources(self, user_id):
        """Get sources accessible to this user"""
        # Check if user is admin
        is_admin = self.db.fetch_one('telegram_archive_bot', '''
            SELECT is_admin FROM users WHERE user_id = %s
        ''', (user_id,))
        
        if is_admin and is_admin['is_admin']:
            # Admins can access all sources
            return self.db.fetch_all('telegram_archive_bot', '''
                SELECT * FROM sources WHERE is_active = TRUE
            ''')
        else:
            # Regular users can only access sources they have permission for
            return self.db.fetch_all('telegram_archive_bot', '''
                SELECT s.* FROM sources s
                JOIN permissions p ON s.id = p.source_id
                WHERE p.user_id = %s AND p.can_search = TRUE AND s.is_active = TRUE
            ''', (user_id,))
            
    def get_source_type_persian(self, source_type):
        """Convert source type to Persian"""
        types = {
            'channel': 'کانال',
            'group': 'گروه معمولی',
            'supergroup': 'سوپرگروه',
            'topic_group': 'گروه با موضوعات'
        }
        return types.get(source_type, source_type)
        
    def get_media_type_persian(self, media_type):
        """Convert media type to Persian"""
        types = {
            'text': 'متن',
            'photo': 'عکس',
            'video': 'ویدیو',
            'document': 'فایل',
            'audio': 'صوت',
            'voice': 'ویس',
            'sticker': 'استیکر',
            'animation': 'گیف',
            'other': 'سایر'
        }
        return types.get(media_type, media_type)

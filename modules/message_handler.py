
import telebot
import json
import logging
import datetime
from telebot import types
from modules.utils import get_extension_from_mime

logger = logging.getLogger(__name__)

class MessageHandler:
    """Handler for processing messages from channels/groups"""
    
    def __init__(self, bot, db_manager, config_manager):
        self.bot = bot
        self.db = db_manager
        self.config = config_manager
        
    def setup_message_handlers(self):
        """Setup message handlers for the bot"""
        @self.bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation'])
        def handle_all_messages(message):
            # Skip messages from private chats (handled elsewhere)
            if message.chat.type == 'private':
                return
                
            try:
                # Process message for archiving
                self.process_message(message)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                
    def process_message(self, message):
        """Process and archive a message if it matches our sources"""
        # Get chat_id
        chat_id = message.chat.id
        
        # Check if this chat is in our sources
        source = self.db.fetch_one('telegram_archive_bot', '''
            SELECT * FROM sources 
            WHERE chat_id = %s AND is_active = TRUE
        ''', (chat_id,))
        
        if not source:
            # Not a monitored source
            return
            
        # Parse filter config
        filter_config = json.loads(source['filter_config'])
        
        # Check if message type is allowed
        if not self.is_message_type_allowed(message, filter_config):
            return
            
        # Check topic if applicable
        if source['type'] == 'topic_group' and message.is_topic_message:
            if not self.is_topic_allowed(message.message_thread_id, source):
                return
                
        # Check keywords filter if configured
        if not self.passes_keyword_filter(message, filter_config):
            return
            
        # If we got here, the message should be archived
        self.archive_message(message, source['id'])
        
    def is_message_type_allowed(self, message, filter_config):
        """Check if message type is allowed by filter config"""
        if message.content_type == 'text' and not filter_config.get('text', True):
            return False
            
        if message.content_type == 'photo' and not filter_config.get('photo', True):
            return False
            
        if message.content_type == 'video' and not filter_config.get('video', True):
            return False
            
        if message.content_type == 'document' and not filter_config.get('document', True):
            return False
            
        if message.content_type == 'audio' and not filter_config.get('audio', True):
            return False
            
        if message.content_type == 'voice' and not filter_config.get('voice', True):
            return False
            
        if message.content_type == 'sticker' and not filter_config.get('sticker', True):
            return False
            
        if message.content_type == 'animation' and not filter_config.get('animation', True):
            return False
            
        return True
        
    def is_topic_allowed(self, topic_id, source):
        """Check if topic is allowed for archiving"""
        topics_config = json.loads(source['topics_config']) if source['topics_config'] else None
        
        if not topics_config:
            return False
            
        # If 'all' is in topics, all topics are allowed
        if 'all' in topics_config:
            return True
            
        # Check if this topic_id is in the allowed list
        return topic_id in topics_config
        
    def passes_keyword_filter(self, message, filter_config):
        """Check if message passes keyword filter"""
        keywords = filter_config.get('keywords', [])
        
        # If no keywords defined, pass the filter
        if not keywords:
            return True
            
        # Get message text
        text = self.get_message_text(message)
        
        if not text:
            return False
            
        # Check if any keyword is in the text
        text = text.lower()
        for keyword in keywords:
            if keyword.lower() in text:
                return True
                
        return False
        
    def get_message_text(self, message):
        """Extract text content from different message types"""
        if message.content_type == 'text':
            return message.text
            
        if message.caption:
            return message.caption
            
        return ''
        
    def archive_message(self, message, source_id):
        """Archive a message to the database"""
        try:
            # Extract message info
            message_id = message.message_id
            sender_id = message.from_user.id if message.from_user else 0
            sender_name = self.get_sender_name(message)
            message_text = self.get_message_text(message)
            message_date = datetime.datetime.fromtimestamp(message.date)
            topic_id = message.message_thread_id if hasattr(message, 'message_thread_id') else None
            
            # Get media info
            media_type, media_file_id = self.get_media_info(message)
            
            # Check if message already exists
            existing = self.db.fetch_one('telegram_archive_bot', '''
                SELECT id FROM archived_messages 
                WHERE source_id = %s AND message_id = %s
            ''', (source_id, message_id))
            
            if existing:
                # Message already archived, update it
                self.db.execute_query('telegram_archive_bot', '''
                    UPDATE archived_messages 
                    SET sender_id = %s, sender_name = %s, message_text = %s, 
                        media_type = %s, media_file_id = %s, topic_id = %s,
                        message_date = %s, archived_at = CURRENT_TIMESTAMP
                    WHERE source_id = %s AND message_id = %s
                ''', (sender_id, sender_name, message_text, media_type, media_file_id, 
                      topic_id, message_date, source_id, message_id))
                
                logger.debug(f"Updated archived message ID {message_id} from source {source_id}")
            else:
                # Insert new archived message
                self.db.execute_query('telegram_archive_bot', '''
                    INSERT INTO archived_messages 
                    (source_id, message_id, sender_id, sender_name, message_text, 
                     media_type, media_file_id, topic_id, message_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (source_id, message_id, sender_id, sender_name, message_text,
                      media_type, media_file_id, topic_id, message_date))
                
                logger.debug(f"Archived new message ID {message_id} from source {source_id}")
                
        except Exception as e:
            logger.error(f"Error archiving message: {e}", exc_info=True)
            
    def get_sender_name(self, message):
        """Get formatted sender name"""
        if not message.from_user:
            return "Unknown"
            
        user = message.from_user
        full_name = user.first_name
        
        if user.last_name:
            full_name += f" {user.last_name}"
            
        if user.username:
            full_name += f" (@{user.username})"
            
        return full_name
        
    def get_media_info(self, message):
        """Extract media type and file_id from message"""
        media_type = 'text'
        file_id = None
        
        if message.content_type == 'photo':
            media_type = 'photo'
            # Get the largest photo (last in the array)
            file_id = message.photo[-1].file_id
            
        elif message.content_type == 'video':
            media_type = 'video'
            file_id = message.video.file_id
            
        elif message.content_type == 'document':
            media_type = 'document'
            file_id = message.document.file_id
            
        elif message.content_type == 'audio':
            media_type = 'audio'
            file_id = message.audio.file_id
            
        elif message.content_type == 'voice':
            media_type = 'voice'
            file_id = message.voice.file_id
            
        elif message.content_type == 'sticker':
            media_type = 'sticker'
            file_id = message.sticker.file_id
            
        elif message.content_type == 'animation':
            media_type = 'animation'
            file_id = message.animation.file_id
            
        return media_type, file_id


import logging
import os
import datetime

def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Get current date for log filename
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = f"logs/telegram_archive_bot_{current_date}.log"
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.info("Logging setup complete")
    
    return logger

def format_timestamp(timestamp):
    """Format a timestamp to a human-readable string"""
    if isinstance(timestamp, datetime.datetime):
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    return str(timestamp)

def get_extension_from_mime(mime_type):
    """Get file extension from MIME type"""
    mime_map = {
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
        'video/mp4': 'mp4',
        'audio/mpeg': 'mp3',
        'audio/ogg': 'ogg',
        'application/pdf': 'pdf',
        'application/zip': 'zip',
        'text/plain': 'txt',
        'application/x-tar': 'tar',
        'application/x-gzip': 'gz',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'doc',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        'application/vnd.ms-excel': 'xls',
    }
    return mime_map.get(mime_type, 'bin')

def split_long_message(text, max_length=4000):
    """Split a long message into multiple parts"""
    if len(text) <= max_length:
        return [text]
        
    parts = []
    while text:
        # Find a good place to split (newline or space)
        if len(text) <= max_length:
            parts.append(text)
            break
            
        split_pos = text[:max_length].rfind('\n')
        if split_pos < 0:
            split_pos = text[:max_length].rfind(' ')
        if split_pos < 0:
            split_pos = max_length
            
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()
        
    return parts

def sanitize_filename(filename):
    """Sanitize a filename to be safe for all filesystems"""
    # Replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
        
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:196] + ext
        
    return filename

def persian_numbers(text):
    """Convert Western Arabic numerals to Persian numerals"""
    mapping = {
        '0': '۰',
        '1': '۱',
        '2': '۲',
        '3': '۳',
        '4': '۴',
        '5': '۵',
        '6': '۶',
        '7': '۷',
        '8': '۸',
        '9': '۹'
    }
    
    result = ''
    for char in str(text):
        result += mapping.get(char, char)
        
    return result

def get_user_mention(user):
    """Get a user mention string"""
    if not user:
        return "کاربر ناشناس"
        
    if user.username:
        return f"@{user.username}"
    else:
        return f"{user.first_name}"

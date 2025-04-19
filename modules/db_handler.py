
import os
import subprocess
import mysql.connector
from mysql.connector import Error
import logging

logger = logging.getLogger(__name__)

def is_mysql_installed():
    """Check if MySQL is installed on the system"""
    try:
        result = subprocess.run(['which', 'mysql'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking MySQL installation: {e}")
        return False

def install_mysql():
    """Install MySQL on Linux system"""
    try:
        logger.info("Installing MySQL...")
        subprocess.run(['apt-get', 'update'], check=True)
        subprocess.run(['apt-get', 'install', '-y', 'mysql-server'], check=True)
        subprocess.run(['service', 'mysql', 'start'], check=True)
        
        # Set up a default root password
        root_password = "ArchiveBot2024!"
        subprocess.run(['mysqladmin', '-u', 'root', 'password', root_password], check=True)
        
        # Create environment variable for database connection
        os.environ['DB_PASSWORD'] = root_password
        logger.info("MySQL installed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to install MySQL: {e}")
        return False

class DatabaseManager:
    """Database manager for handling MySQL operations"""
    
    def __init__(self):
        # Default credentials
        self.host = "localhost"
        self.user = "root"
        self.password = os.getenv('DB_PASSWORD', "ArchiveBot2024!")
        self.connection = None
        
    def connect(self):
        """Connect to MySQL server"""
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password
                )
                logger.info("Connected to MySQL server")
            return self.connection
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            return None
    
    def create_database(self, db_name):
        """Create a database if it doesn't exist"""
        try:
            connection = self.connect()
            if connection:
                cursor = connection.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                connection.commit()
                logger.info(f"Database '{db_name}' created or already exists")
                return True
        except Error as e:
            logger.error(f"Error creating database: {e}")
        return False
    
    def execute_query(self, db_name, query, params=None):
        """Execute a query on the specified database"""
        try:
            connection = self.connect()
            if connection:
                cursor = connection.cursor(dictionary=True)
                cursor.execute(f"USE {db_name}")
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                connection.commit()
                return cursor
        except Error as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
        return None
    
    def fetch_all(self, db_name, query, params=None):
        """Execute a query and fetch all results"""
        cursor = self.execute_query(db_name, query, params)
        if cursor:
            result = cursor.fetchall()
            cursor.close()
            return result
        return []
    
    def fetch_one(self, db_name, query, params=None):
        """Execute a query and fetch one result"""
        cursor = self.execute_query(db_name, query, params)
        if cursor:
            result = cursor.fetchone()
            cursor.close()
            return result
        return None
    
    def close(self):
        """Close the database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("MySQL connection closed")

def setup_database(db_manager):
    """Setup all required databases and tables"""
    
    # Check if MySQL is installed, if not, install it
    if not is_mysql_installed():
        if not install_mysql():
            logger.error("Failed to install MySQL. Exiting...")
            return False
    
    # Create main bot database
    db_manager.create_database('telegram_archive_bot')
    
    # Create users table
    db_manager.execute_query('telegram_archive_bot', '''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT UNIQUE,
            username VARCHAR(255),
            is_admin BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create config table
    db_manager.execute_query('telegram_archive_bot', '''
        CREATE TABLE IF NOT EXISTS config (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) UNIQUE,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    ''')
    
    # Create sources table (channels and groups to archive)
    db_manager.execute_query('telegram_archive_bot', '''
        CREATE TABLE IF NOT EXISTS sources (
            id INT AUTO_INCREMENT PRIMARY KEY,
            type ENUM('channel', 'group', 'supergroup', 'topic_group'),
            chat_id BIGINT,
            chat_title VARCHAR(255),
            chat_username VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            filter_config JSON,
            topics_config JSON,
            added_by BIGINT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create access permissions table
    db_manager.execute_query('telegram_archive_bot', '''
        CREATE TABLE IF NOT EXISTS permissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id BIGINT,
            source_id INT,
            can_search BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (source_id) REFERENCES sources(id),
            UNIQUE KEY user_source (user_id, source_id)
        )
    ''')
    
    # Create archived messages table
    db_manager.execute_query('telegram_archive_bot', '''
        CREATE TABLE IF NOT EXISTS archived_messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            source_id INT,
            message_id BIGINT,
            sender_id BIGINT,
            sender_name VARCHAR(255),
            message_text TEXT,
            media_type ENUM('text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation', 'other'),
            media_file_id VARCHAR(255),
            topic_id INT NULL,
            message_date TIMESTAMP,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (source_id) REFERENCES sources(id)
        )
    ''')
    
    # Create backup logs table
    db_manager.execute_query('telegram_archive_bot', '''
        CREATE TABLE IF NOT EXISTS backup_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            file_name VARCHAR(255),
            file_size BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('success', 'failed'),
            message TEXT
        )
    ''')
    
    # Insert default config values if not exists
    default_configs = [
        ('bot_enabled', 'true'),
        ('admin_chat_id', ''),
        ('backup_interval', '1440'),  # 24 hours in minutes
        ('backup_channel_id', ''),
        ('broadcast_welcome', 'به ربات آرشیو خوش آمدید!')
    ]
    
    for name, value in default_configs:
        db_manager.execute_query('telegram_archive_bot', 
                              "INSERT IGNORE INTO config (name, value) VALUES (%s, %s)",
                              (name, value))
    
    # Add default admin if specified in environment variables
    admin_id = os.getenv('ADMIN_ID')
    if admin_id:
        db_manager.execute_query('telegram_archive_bot', '''
            INSERT INTO users (user_id, username, is_admin) 
            VALUES (%s, %s, TRUE)
            ON DUPLICATE KEY UPDATE is_admin = TRUE
        ''', (admin_id, 'DefaultAdmin'))
    
    logger.info("Database setup completed successfully")
    return True

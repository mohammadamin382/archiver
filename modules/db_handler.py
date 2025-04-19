
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

def is_mysql_running():
    """Check if MySQL service is running"""
    try:
        # Try both systemctl and service commands
        systemctl_result = subprocess.run(
            ['systemctl', 'is-active', 'mysql'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if systemctl_result.stdout.strip() == 'active':
            return True
            
        # Try with service
        service_result = subprocess.run(
            ['service', 'mysql', 'status'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        return service_result.returncode == 0
    except Exception as e:
        logger.warning(f"Error checking if MySQL is running: {e}")
        # Try one more method - check if port 3306 is in use
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 3306))
            sock.close()
            return result == 0
        except:
            return False

def find_available_port(start_port=3306, end_port=3350):
    """Find an available port for MySQL"""
    import socket
    for port in range(start_port, end_port + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result != 0:  # Port is available
                return port
        except:
            continue
    return None

def install_mysql():
    """Install MySQL on Linux system"""
    try:
        # Check if MySQL is already running
        if is_mysql_running():
            logger.info("MySQL is already running. Trying to use the existing installation.")
            return True
            
        logger.info("Installing MySQL...")
        # Update package lists
        subprocess.run(['apt-get', 'update'], check=True)
        
        # Try noninteractive installation to avoid prompts
        env = os.environ.copy()
        env["DEBIAN_FRONTEND"] = "noninteractive"
        
        # Set MySQL root password
        root_password = "ArchiveBot2024!"
        env["MYSQL_ROOT_PASSWORD"] = root_password
        
        # Install MySQL
        try:
            subprocess.run(
                ['apt-get', 'install', '-y', 'mysql-server'],
                env=env,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to install MySQL with apt: {e}")
            # Try installing MariaDB as a fallback
            try:
                logger.info("Trying to install MariaDB as an alternative...")
                subprocess.run(
                    ['apt-get', 'install', '-y', 'mariadb-server'],
                    env=env,
                    check=True
                )
            except subprocess.CalledProcessError as e2:
                logger.error(f"Failed to install MariaDB: {e2}")
                return False
        
        # Try to start the service
        try:
            subprocess.run(['service', 'mysql', 'start'], check=True)
        except:
            try:
                subprocess.run(['service', 'mariadb', 'start'], check=True)
            except:
                logger.warning("Could not start service, it might be already running")
        
        # Set up a default root password (might fail if already set)
        try:
            subprocess.run(
                ['mysqladmin', '-u', 'root', 'password', root_password],
                stderr=subprocess.PIPE,
                check=False  # Don't fail if password is already set
            )
        except:
            logger.warning("Could not set root password, it might be already set")
            
        # Create environment variable for database connection
        os.environ['DB_PASSWORD'] = root_password
        logger.info("MySQL/MariaDB setup completed")
        return True
    except Exception as e:
        logger.error(f"Failed to install MySQL: {e}")
        return False

class DatabaseManager:
    """Database manager for handling MySQL operations"""
    
    def __init__(self):
        # Default credentials
        self.host = os.getenv('DB_HOST', "localhost")
        self.user = os.getenv('DB_USER', "root")
        self.password = os.getenv('DB_PASSWORD', "ArchiveBot2024!")
        self.port = int(os.getenv('DB_PORT', "3306"))
        self.connection = None
        
    def connect(self):
        """Connect to MySQL server"""
        try:
            if self.connection is None or not self.connection.is_connected():
                self.connection = mysql.connector.connect(
                    host=self.host,
                    user=self.user,
                    password=self.password,
                    port=self.port
                )
                logger.info(f"Connected to MySQL server at {self.host}:{self.port}")
            return self.connection
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            # Try alternate ports if connection failed
            if self.port == 3306 and e.errno == 2003:  # Connection refused
                alt_port = find_available_port()
                if alt_port and alt_port != self.port:
                    logger.info(f"Trying alternate port: {alt_port}")
                    try:
                        self.port = alt_port
                        self.connection = mysql.connector.connect(
                            host=self.host,
                            user=self.user,
                            password=self.password,
                            port=self.port
                        )
                        os.environ['DB_PORT'] = str(alt_port)
                        logger.info(f"Connected to MySQL server at {self.host}:{self.port}")
                        return self.connection
                    except Error as e2:
                        logger.error(f"Error connecting to alternate port: {e2}")
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

def get_db_manager():
    """Get appropriate database manager based on DB_TYPE"""
    db_type = os.getenv('DB_TYPE', 'mysql').lower()
    
    if db_type == 'sqlite':
        # Import SQLite manager
        from .sqlite_handler import SQLiteManager
        logger.info("Using SQLite as database backend")
        return SQLiteManager()
    else:
        # Use MySQL manager
        logger.info("Using MySQL as database backend")
        return DatabaseManager()

def setup_database(db_manager):
    """Setup all required databases and tables"""
    
    # Get database type
    db_type = os.getenv('DB_TYPE', 'mysql').lower()
    
    if db_type == 'sqlite':
        # SQLite setup is simpler - just create tables
        logger.info("Setting up SQLite database")
        db_manager.create_database()
        
        # Insert default config values
        default_configs = [
            ('bot_enabled', 'true'),
            ('admin_chat_id', ''),
            ('backup_interval', '1440'),  # 24 hours in minutes
            ('backup_channel_id', ''),
            ('broadcast_welcome', 'به ربات آرشیو خوش آمدید!')
        ]
        
        for name, value in default_configs:
            db_manager.execute_query('ignored', 
                                  "INSERT OR IGNORE INTO config (name, value) VALUES (?, ?)",
                                  (name, value))
        
        # Add default admin if specified
        admin_id = os.getenv('ADMIN_ID')
        if admin_id:
            db_manager.execute_query('ignored', '''
                INSERT OR IGNORE INTO users (user_id, username, is_admin) 
                VALUES (?, ?, 1)
            ''', (admin_id, 'DefaultAdmin'))
            
            # Update if exists
            db_manager.execute_query('ignored', '''
                UPDATE users SET is_admin = 1 WHERE user_id = ?
            ''', (admin_id,))
    else:
        # MySQL setup
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

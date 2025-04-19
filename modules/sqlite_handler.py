
import os
import sqlite3
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class SQLiteManager:
    """SQLite database manager for handling operations"""
    
    def __init__(self):
        # Get SQLite file path from environment
        self.db_file = os.getenv('DB_FILE', 'telegram_archive_bot.db')
        self.connection = None
        
    def connect(self):
        """Connect to SQLite database"""
        try:
            if self.connection is None:
                self.connection = sqlite3.connect(self.db_file)
                # Enable foreign keys
                self.connection.execute("PRAGMA foreign_keys = ON")
                # Return dictionaries instead of tuples
                self.connection.row_factory = sqlite3.Row
                logger.info(f"Connected to SQLite database: {self.db_file}")
            return self.connection
        except Exception as e:
            logger.error(f"Error connecting to SQLite: {e}")
            return None
    
    def create_database(self, db_name=None):
        """Create tables in SQLite database (db_name is ignored)"""
        try:
            connection = self.connect()
            if connection:
                cursor = connection.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER UNIQUE,
                        username TEXT,
                        is_admin INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create config table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create sources table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sources (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT CHECK(type IN ('channel', 'group', 'supergroup', 'topic_group')),
                        chat_id INTEGER,
                        chat_title TEXT,
                        chat_username TEXT,
                        is_active INTEGER DEFAULT 1,
                        filter_config TEXT, -- JSON
                        topics_config TEXT, -- JSON
                        added_by INTEGER,
                        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create permissions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS permissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        source_id INTEGER,
                        can_search INTEGER DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users(user_id),
                        FOREIGN KEY (source_id) REFERENCES sources(id),
                        UNIQUE (user_id, source_id)
                    )
                ''')
                
                # Create archived messages table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS archived_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_id INTEGER,
                        message_id INTEGER,
                        sender_id INTEGER,
                        sender_name TEXT,
                        message_text TEXT,
                        media_type TEXT CHECK(media_type IN 
                            ('text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker', 'animation', 'other')),
                        media_file_id TEXT,
                        topic_id INTEGER,
                        message_date TIMESTAMP,
                        archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (source_id) REFERENCES sources(id)
                    )
                ''')
                
                # Create backup logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS backup_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_name TEXT,
                        file_size INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT CHECK(status IN ('success', 'failed')),
                        message TEXT
                    )
                ''')
                
                connection.commit()
                logger.info("SQLite tables created successfully")
                return True
        except Exception as e:
            logger.error(f"Error creating SQLite tables: {e}")
        return False
    
    def execute_query(self, db_name, query, params=None):
        """Execute a query on the database (db_name is ignored)"""
        try:
            # Convert MySQL %s style parameters to SQLite ? style
            if params and '%s' in query:
                query = query.replace('%s', '?')
                
            connection = self.connect()
            if connection:
                cursor = connection.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                connection.commit()
                return cursor
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Params: {params}")
        return None
    
    def fetch_all(self, db_name, query, params=None):
        """Execute a query and fetch all results (db_name is ignored)"""
        cursor = self.execute_query(db_name, query, params)
        if cursor:
            result = [dict(row) for row in cursor.fetchall()]
            return result
        return []
    
    def fetch_one(self, db_name, query, params=None):
        """Execute a query and fetch one result (db_name is ignored)"""
        cursor = self.execute_query(db_name, query, params)
        if cursor:
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None
    
    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("SQLite connection closed")

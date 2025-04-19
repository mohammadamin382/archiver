
#!/usr/bin/env python3
"""
Advanced Installation script for telegram-archive-bot
This script handles complete setup with Docker support and management options
"""

import os
import sys
import subprocess
import getpass
import shutil
import time
import socket
from dotenv import load_dotenv

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)

def print_success(text):
    """Print a success message"""
    print(f"\n✅ {text}")

def print_error(text):
    """Print an error message"""
    print(f"\n❌ {text}")

def print_info(text):
    """Print an info message"""
    print(f"\nℹ️ {text}")

def print_menu():
    """Print the main menu"""
    print_header("ربات آرشیو تلگرام | منوی اصلی")
    print("\n1️⃣ شروع نصب و راه‌اندازی")
    print("2️⃣ حذف ایمیج داکر")
    print("3️⃣ حذف کامل پروژه")
    print("0️⃣ خروج")
    
    choice = input("\n👉 لطفاً گزینه مورد نظر را انتخاب کنید: ")
    return choice

def check_mysql_service():
    """Check MySQL/MariaDB service status and try to start it if not running"""
    try:
        # Check if service is running
        service_name = None
        for svc in ['mysql', 'mariadb', 'mysqld']:
            try:
                result = subprocess.run(
                    ['service', svc, 'status'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                if result.returncode == 0:
                    service_name = svc
                    print_success(f"سرویس {svc} در حال اجرا است.")
                    return True
            except:
                pass
                
        # Try to start service if not running
        if service_name:
            try:
                subprocess.run(['service', service_name, 'start'], check=True)
                print_success(f"سرویس {service_name} با موفقیت راه‌اندازی شد.")
                return True
            except:
                print_error(f"خطا در راه‌اندازی سرویس {service_name}")
        
        return False
    except Exception as e:
        print_error(f"خطا در بررسی وضعیت سرویس دیتابیس: {e}")
        return False

def find_available_port(start_port=3306, end_port=3350):
    """Find an available port for MySQL"""
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

def create_env_file():
    """Create .env file with user input"""
    print_header("تنظیم فایل .env")
    
    if os.path.exists('.env'):
        overwrite = input("\nفایل .env قبلاً وجود دارد. آیا می‌خواهید آن را بازنویسی کنید؟ (y/n): ")
        if overwrite.lower() != 'y':
            print_info("از فایل .env موجود استفاده می‌شود.")
            return True
    
    bot_token = input("\n👉 توکن ربات تلگرام را وارد کنید: ")
    if not bot_token:
        print_error("توکن ربات الزامی است!")
        return False
    
    admin_id = input("\n👉 شناسه عددی کاربر ادمین را وارد کنید: ")
    if not admin_id.isdigit():
        print_error("شناسه ادمین باید عدد باشد!")
        return False
    
    # Ask for database type
    print_header("انتخاب نوع دیتابیس")
    print("\n1️⃣ استفاده از MySQL/MariaDB (مناسب برای پروژه‌های بزرگ)")
    print("2️⃣ استفاده از SQLite (نصب آسان، بدون نیاز به تنظیمات، مناسب برای پروژه‌های کوچک)")
    
    db_choice = input("\n👉 لطفاً نوع دیتابیس را انتخاب کنید (1/2): ")
    
    use_sqlite = db_choice == "2"
    
    if use_sqlite:
        # SQLite setup - simple and automatic
        print_success("SQLite انتخاب شد. نیازی به تنظیمات بیشتر نیست.")
        
        # Create .env with SQLite config
        with open('.env', 'w') as f:
            f.write(f"BOT_TOKEN={bot_token}\n")
            f.write(f"ADMIN_ID={admin_id}\n")
            f.write(f"DB_TYPE=sqlite\n")
            f.write(f"DB_FILE=telegram_archive_bot.db\n")
        
        print_success("فایل .env با موفقیت برای SQLite ایجاد شد.")
        return True
    else:
        # MySQL setup - with more configuration options
        print_success("MySQL/MariaDB انتخاب شد.")
        
        # Default MySQL settings
        db_host = "localhost"
        db_user = "root"
        db_password = "ArchiveBot2024!"
        db_port = 3306
        
        # Try to automatically detect MySQL connection
        use_existing_db = False
        try:
            # Check if MySQL service is running
            check_mysql_service()
            
            # Check for MySQL port
            current_port = None
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', 3306))
            sock.close()
            
            if result == 0:  # Default port in use
                current_port = 3306
            else:
                # Find if MySQL is running on another port
                for test_port in range(3307, 3350):
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = sock.connect_ex(('127.0.0.1', test_port))
                    sock.close()
                    if result == 0:
                        current_port = test_port
                        break
                        
            if current_port:
                db_port = current_port
                print_info(f"MySQL پیدا شد و در حال اجرا در پورت {db_port} است.")
                use_existing_db = True
            else:
                # Find an available port
                available_port = find_available_port()
                if available_port:
                    db_port = available_port
                    print_info(f"پورت {db_port} برای MySQL در دسترس است.")
                else:
                    print_info("پورت مناسبی برای MySQL پیدا نشد. از پورت پیش‌فرض استفاده می‌شود.")
        except Exception as e:
            print_error(f"خطا در تشخیص خودکار دیتابیس: {e}")
        
        if use_existing_db:
            db_host_input = input(f"\n👉 آدرس هاست دیتابیس (پیش‌فرض: {db_host}): ") or db_host
            db_user_input = input(f"\n👉 نام کاربری دیتابیس (پیش‌فرض: {db_user}): ") or db_user
            db_password_input = getpass.getpass(f"\n👉 رمز عبور دیتابیس (پیش‌فرض: [رمز پیش‌فرض]): ")
            db_port_input = input(f"\n👉 پورت دیتابیس (پیش‌فرض: {db_port}): ") or str(db_port)
            
            if db_host_input:
                db_host = db_host_input
            if db_user_input:
                db_user = db_user_input
            if db_password_input:
                db_password = db_password_input
            if db_port_input and db_port_input.isdigit():
                db_port = int(db_port_input)
        else:
            print_info("تنظیمات دیتابیس به صورت خودکار تعیین می‌شود.")
        
        # Create .env with MySQL config
        with open('.env', 'w') as f:
            f.write(f"BOT_TOKEN={bot_token}\n")
            f.write(f"ADMIN_ID={admin_id}\n")
            f.write(f"DB_TYPE=mysql\n")
            f.write(f"DB_HOST={db_host}\n")
            f.write(f"DB_USER={db_user}\n")
            f.write(f"DB_PASSWORD={db_password}\n")
            f.write(f"DB_PORT={db_port}\n")
        
        print_success("فایل .env با موفقیت برای MySQL ایجاد شد.")
        return True

def install_dependencies():
    """Install required dependencies"""
    print_header("نصب وابستگی‌ها")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
        print_success("وابستگی‌ها با موفقیت نصب شدند.")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"خطا در نصب وابستگی‌ها: {e}")
        return False

def check_database_connection():
    """Check database connection based on configured type"""
    # Load env variables
    load_dotenv()
    
    db_type = os.getenv('DB_TYPE', 'mysql')
    
    if db_type.lower() == 'sqlite':
        try:
            # Check for sqlite3 module
            import sqlite3
            print_success("ماژول sqlite3 موجود است.")
            
            # SQLite doesn't need connection check - it will create db when needed
            db_file = os.getenv('DB_FILE', 'telegram_archive_bot.db')
            db_dir = os.path.dirname(db_file)
            
            # Make sure the directory exists if specified
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)
                print_info(f"دایرکتوری {db_dir} برای فایل دیتابیس ایجاد شد.")
            
            # Try to create a test connection
            try:
                conn = sqlite3.connect(db_file)
                conn.close()
                print_success(f"اتصال به دیتابیس SQLite با موفقیت انجام شد. (فایل: {db_file})")
                return True
            except Exception as e:
                print_error(f"خطا در اتصال به دیتابیس SQLite: {e}")
                return False
        except ImportError:
            print_error("ماژول sqlite3 یافت نشد.")
            return False
    else:
        # MySQL connection check
        try:
            # Try to import mysql connector
            import mysql.connector
            print_success("ماژول mysql.connector موجود است.")
            
            # Try connection with parameters from .env
            db_host = os.getenv('DB_HOST', 'localhost')
            db_user = os.getenv('DB_USER', 'root')
            db_password = os.getenv('DB_PASSWORD', 'ArchiveBot2024!')
            db_port = int(os.getenv('DB_PORT', '3306'))
            
            # Test connection with parameters from .env
            try:
                conn = mysql.connector.connect(
                    host=db_host,
                    user=db_user,
                    password=db_password,
                    port=db_port
                )
                conn.close()
                print_success(f"اتصال به دیتابیس MySQL با موفقیت انجام شد. (کاربر: {db_user}@{db_host}:{db_port})")
                return True
            except Exception as e:
                print_error(f"خطا در اتصال به دیتابیس MySQL با پارامترهای فعلی: {e}")
                
                # Try with different common ports if default port fails
                alt_ports = [3307, 3308, 3309, 3310, 3350]
                for alt_port in alt_ports:
                    if alt_port == db_port:
                        continue
                        
                    try:
                        print_info(f"تلاش برای اتصال با پورت {alt_port}...")
                        conn = mysql.connector.connect(
                            host=db_host,
                            user=db_user,
                            password=db_password,
                            port=alt_port
                        )
                        conn.close()
                        
                        # Update .env with new port
                        print_success(f"اتصال به دیتابیس با موفقیت در پورت {alt_port} انجام شد.")
                        with open('.env', 'r') as f:
                            env_content = f.read()
                        
                        if 'DB_PORT=' in env_content:
                            env_content = '\n'.join([
                                line if not line.startswith('DB_PORT=') else f'DB_PORT={alt_port}'
                                for line in env_content.split('\n')
                            ])
                        else:
                            env_content += f"\nDB_PORT={alt_port}"
                        
                        with open('.env', 'w') as f:
                            f.write(env_content)
                            
                        return True
                    except:
                        continue
                
                # If we get here, all connection attempts failed
                return False
                
        except ImportError:
            print_error("ماژول mysql.connector یافت نشد.")
            return False

# Maintain backward compatibility
def check_mysql_connection():
    """Legacy function for compatibility"""
    load_dotenv()
    db_type = os.getenv('DB_TYPE', 'mysql')
    
    if db_type.lower() == 'sqlite':
        return True  # Always return success for SQLite
    else:
        return check_database_connection()

def check_docker_installed():
    """Check if Docker is installed"""
    try:
        result = subprocess.run(["docker", "--version"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
        if result.returncode == 0:
            print_success(f"داکر نصب شده است: {result.stdout.strip()}")
            return True
        else:
            print_error("داکر نصب نشده است.")
            return False
    except Exception:
        print_error("داکر نصب نشده است.")
        return False


def set_mysql_password(is_mariadb=False):
    """Try different methods to set MySQL root password"""
    db_password = os.getenv('DB_PASSWORD', 'ArchiveBot2024!')
    service_name = "mariadb" if is_mariadb else "mysql"
    
    methods = [
        # Method 1: ALTER USER (MySQL 5.7+)
        ["mysql", "-e", f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{db_password}';"],
        
        # Method 2: SET PASSWORD (older MySQL)
        ["mysql", "-e", f"SET PASSWORD FOR 'root'@'localhost' = PASSWORD('{db_password}');"],
        
        # Method 3: mysqladmin
        ["mysqladmin", "-u", "root", "password", db_password],
        
        # Method 4: Try with sudo
        ["sudo", "mysql", "-e", f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{db_password}';"],
        
        # Method 5: Try with sudo and no password (common in fresh installs)
        ["sudo", "mysql", "-u", "root", "-e", f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{db_password}';"]
    ]
    
    for method in methods:
        try:
            result = subprocess.run(
                method,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False  # Don't fail on error
            )
            
            if result.returncode == 0:
                print_success(f"رمز عبور root با موفقیت تنظیم شد (روش {methods.index(method)+1}).")
                return True
        except:
            continue
    
    print_warning("تنظیم رمز عبور با تمام روش‌ها ناموفق بود.")
    return False

def print_warning(text):
    """Print a warning message"""
    print(f"\n⚠️ {text}")


def check_docker_compose_installed():
    """Check if Docker Compose is installed"""
    try:
        result = subprocess.run(["docker-compose", "--version"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
        if result.returncode == 0:
            print_success(f"داکر کامپوز نصب شده است: {result.stdout.strip()}")
            return True
        
        # Alternative command for newer Docker versions
        result = subprocess.run(["docker", "compose", "version"], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
        if result.returncode == 0:
            print_success(f"داکر کامپوز نصب شده است: {result.stdout.strip()}")
            return True
        
        print_error("داکر کامپوز نصب نشده است.")
        return False
    except Exception:
        print_error("داکر کامپوز نصب نشده است.")
        return False

def create_docker_compose_file():
    """Create docker-compose.yml file based on database type"""
    # Get database info from .env
    load_dotenv()
    db_type = os.getenv('DB_TYPE', 'mysql')
    
    if db_type.lower() == 'sqlite':
        # Docker setup for SQLite
        content = """version: '3.8'

services:
  bot:
    build: .
    restart: always
    volumes:
      - ./logs:/app/logs
      - ./backups:/app/backups
      - ./data:/app/data
    env_file:
      - .env

volumes:
  sqlite_data:
"""
    else:
        # Docker setup for MySQL
        db_port = os.getenv('DB_PORT', '3306')
        
        content = f"""version: '3.8'

services:
  bot:
    build: .
    restart: always
    depends_on:
      - db
    volumes:
      - ./logs:/app/logs
      - ./backups:/app/backups
    env_file:
      - .env
    networks:
      - bot_network

  db:
    image: mysql:8.0
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: ${{DB_PASSWORD}}
      MYSQL_DATABASE: telegram_archive_bot
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "{db_port}:3306"
    networks:
      - bot_network
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

volumes:
  mysql_data:

networks:
  bot_network:
    driver: bridge
"""
    
    with open('docker-compose.yml', 'w') as f:
        f.write(content)
    
    print_success("فایل docker-compose.yml با موفقیت ایجاد شد.")

def create_dockerfile():
    """Create Dockerfile"""
    content = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
"""
    
    with open('Dockerfile', 'w') as f:
        f.write(content)
    
    print_success("فایل Dockerfile با موفقیت ایجاد شد.")

def update_env_for_docker():
    """Update .env file for Docker setup based on database type"""
    # Load current .env
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    admin_id = os.getenv('ADMIN_ID')
    db_type = os.getenv('DB_TYPE', 'mysql')
    
    # Write new .env for Docker
    with open('.env', 'w') as f:
        f.write(f"BOT_TOKEN={bot_token}\n")
        f.write(f"ADMIN_ID={admin_id}\n")
        
        if db_type.lower() == 'sqlite':
            # SQLite configuration for Docker
            f.write(f"DB_TYPE=sqlite\n")
            f.write(f"DB_FILE=/app/data/telegram_archive_bot.db\n")
        else:
            # MySQL configuration for Docker
            db_password = os.getenv('DB_PASSWORD', 'ArchiveBot2024!')
            f.write(f"DB_TYPE=mysql\n")
            f.write(f"DB_HOST=db\n")  # Use Docker service name
            f.write(f"DB_USER=root\n")
            f.write(f"DB_PASSWORD={db_password}\n")
    
    print_success("فایل .env برای استفاده با داکر بروزرسانی شد.")

def detect_docker_compose_command():
    """Detect the available docker-compose command"""
    try:
        # Try the old docker-compose command
        result = subprocess.run(
            ["docker-compose", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode == 0:
            return "docker-compose"
    except:
        pass
        
    try:
        # Try the new docker compose command
        result = subprocess.run(
            ["docker", "compose", "version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if result.returncode == 0:
            return "docker compose"
    except:
        pass
        
    # If we get here, no docker-compose command was found
    return None

def install_docker_compose():
    """Try to install Docker Compose"""
    try:
        print_info("در حال نصب Docker Compose...")
        
        # Method 1: Using apt-get
        try:
            subprocess.run(["apt-get", "update"], check=True)
            subprocess.run(["apt-get", "install", "-y", "docker-compose"], check=True)
            return True
        except:
            pass
            
        # Method 2: Using Python pip
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "docker-compose"], check=True)
            return True
        except:
            pass
            
        # Method 3: Using curl (official installation)
        try:
            subprocess.run([
                "curl", "-L", 
                "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)",
                "-o", "/usr/local/bin/docker-compose"
            ], check=True)
            subprocess.run(["chmod", "+x", "/usr/local/bin/docker-compose"], check=True)
            return True
        except:
            pass
            
        return False
    except Exception as e:
        print_error(f"خطا در نصب Docker Compose: {e}")
        return False

def run_with_docker():
    """Run the application with Docker"""
    print_header("راه‌اندازی با داکر")
    
    # Detect docker-compose command
    docker_compose_cmd = detect_docker_compose_command()
    
    if not docker_compose_cmd:
        print_info("Docker Compose یافت نشد. در حال تلاش برای نصب آن...")
        if install_docker_compose():
            print_success("Docker Compose با موفقیت نصب شد.")
            docker_compose_cmd = detect_docker_compose_command()
        else:
            print_error("نصب Docker Compose ناموفق بود.")
            print_info("آیا می‌خواهید بدون داکر ادامه دهید؟")
            continue_without_docker = input("(y/n): ")
            
            if continue_without_docker.lower() == 'y':
                return run_without_docker()
            else:
                return False
    
    # Create data directory for SQLite if needed
    load_dotenv()
    db_type = os.getenv('DB_TYPE', 'mysql')
    if db_type.lower() == 'sqlite':
        if not os.path.exists('data'):
            os.makedirs('data')
            print_success("دایرکتوری data برای SQLite ایجاد شد.")
    
    try:
        # Split the command into parts for subprocess
        cmd_parts = docker_compose_cmd.split()
        
        # Create command list
        up_cmd = cmd_parts + ["up", "--build", "-d"]
        
        print_info(f"در حال اجرای دستور: {' '.join(up_cmd)}")
        
        # Build and run with docker-compose
        subprocess.run(up_cmd, check=True)
        print_success("ربات با موفقیت در داکر راه‌اندازی شد.")
        print_info("برای مشاهده لاگ‌ها از دستور زیر استفاده کنید:")
        print(f"   {docker_compose_cmd} logs -f bot")
        return True
    except Exception as e:
        print_error(f"خطا در راه‌اندازی داکر: {e}")
        
        print_info("آیا می‌خواهید بدون داکر ادامه دهید؟")
        continue_without_docker = input("(y/n): ")
        
        if continue_without_docker.lower() == 'y':
            return run_without_docker()
        else:
            return False

def run_without_docker():
    """Run the application directly"""
    print_header("راه‌اندازی بدون داکر")
    
    load_dotenv()
    db_type = os.getenv('DB_TYPE', 'mysql')
    
    if db_type.lower() == 'sqlite':
        print_info("استفاده از SQLite به عنوان دیتابیس")
        db_file = os.getenv('DB_FILE', 'telegram_archive_bot.db')
        print_info(f"فایل دیتابیس: {db_file}")
        
        # No need for additional setup with SQLite
        print_success("SQLite نیازی به تنظیمات اضافی ندارد.")
        
    else:
        print_info("استفاده از MySQL به عنوان دیتابیس")
        # Check database connection
        if not check_mysql_connection():
            print_info("آیا می‌خواهید MySQL به صورت خودکار نصب شود؟ (فقط برای سیستم‌های لینوکس)")
            install_mysql = input("(y/n): ")
            
            if install_mysql.lower() == 'y':
                try:
                    # First check if service exists but is just not running
                    if check_mysql_service():
                        # Service is now running, try to connect again
                        if check_mysql_connection():
                            print_success("اتصال به دیتابیس با موفقیت انجام شد.")
                        else:
                            print_error("سرویس در حال اجراست اما اتصال برقرار نیست. احتمالاً مشکل با رمز عبور.")
                            # Try to reset root password
                            try_reset_password = input("آیا می‌خواهید رمز عبور root را بازنشانی کنید؟ (y/n): ")
                            if try_reset_password.lower() == 'y':
                                set_mysql_password()
                    else:
                        # Install MySQL with noninteractive mode to avoid prompts
                        env = os.environ.copy()
                        env["DEBIAN_FRONTEND"] = "noninteractive"
                        db_password = os.getenv('DB_PASSWORD', 'ArchiveBot2024!')
                        env["MYSQL_ROOT_PASSWORD"] = db_password
                        
                        print_info("در حال نصب MySQL...")
                        subprocess.run(["apt-get", "update"], check=True)
                        
                        try:
                            # Try MySQL first
                            subprocess.run([
                                "apt-get", "install", "-y", "mysql-server"
                            ], env=env, check=True)
                            
                            print_info("در حال راه‌اندازی سرویس MySQL...")
                            subprocess.run(["service", "mysql", "start"], check=True)
                            
                            # Try setting root password
                            set_mysql_password()
                            
                        except Exception as e:
                            print_error(f"خطا در نصب MySQL: {e}")
                            
                            # Try MariaDB as fallback
                            try:
                                print_info("در حال نصب MariaDB به عنوان جایگزین...")
                                subprocess.run([
                                    "apt-get", "install", "-y", "mariadb-server"
                                ], env=env, check=True)
                                
                                print_info("در حال راه‌اندازی سرویس MariaDB...")
                                subprocess.run(["service", "mariadb", "start"], check=True)
                                
                                # Try setting root password
                                set_mysql_password(is_mariadb=True)
                                
                            except Exception as e2:
                                print_error(f"خطا در نصب MariaDB: {e2}")
                                return False
                    
                    # Check connection again after installation
                    if check_mysql_connection():
                        print_success("اتصال به دیتابیس با موفقیت انجام شد.")
                    else:
                        print_error("نصب انجام شد اما اتصال برقرار نیست.")
                        return False
                    
                except Exception as e:
                    print_error(f"خطا در نصب دیتابیس: {e}")
                    return False
            else:
                print_error("اتصال به دیتابیس برقرار نیست. لطفاً دیتابیس را نصب و پیکربندی کنید.")
                return False
        
        # Create database for MySQL
        try:
            import mysql.connector
            
            db_host = os.getenv('DB_HOST', 'localhost')
            db_user = os.getenv('DB_USER', 'root')
            db_password = os.getenv('DB_PASSWORD', 'ArchiveBot2024!')
            
            # Connect to MySQL
            conn = mysql.connector.connect(
                host=db_host,
                user=db_user,
                password=db_password
            )
            
            # Create database
            cursor = conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS telegram_archive_bot")
            print_success("دیتابیس با موفقیت ایجاد شد.")
            
            conn.close()
        except Exception as e:
            print_error(f"خطا در ایجاد دیتابیس: {e}")
            return False
    
    try:
        # Run the bot
        print_info("در حال راه‌اندازی ربات...")
        process = subprocess.Popen([sys.executable, "main.py"])
        
        print_success("ربات با موفقیت راه‌اندازی شد.")
        print_info("برای توقف ربات، کلید CTRL+C را فشار دهید.")
        
        # Wait for user to stop the bot
        try:
            process.wait()
        except KeyboardInterrupt:
            process.terminate()
            print_info("ربات متوقف شد.")
        
        return True
    except Exception as e:
        print_error(f"خطا در راه‌اندازی ربات: {e}")
        return False

def remove_docker_images():
    """Remove Docker images"""
    print_header("حذف ایمیج‌های داکر")
    
    if not check_docker_installed():
        print_error("داکر نصب نشده است.")
        return False
    
    try:
        # Stop and remove containers
        subprocess.run(["docker-compose", "down"], stderr=subprocess.STDOUT)
    except:
        try:
            # Try alternative command
            subprocess.run(["docker", "compose", "down"], stderr=subprocess.STDOUT)
        except:
            pass
    
    try:
        # Remove images
        project_name = os.path.basename(os.getcwd())
        image_name = f"{project_name.lower()}_bot"
        
        result = subprocess.run(["docker", "images", "-q", image_name], 
                              stdout=subprocess.PIPE, 
                              text=True)
        
        if result.stdout.strip():
            subprocess.run(["docker", "rmi", result.stdout.strip()], check=True)
            print_success("ایمیج‌های داکر با موفقیت حذف شدند.")
        else:
            print_info("هیچ ایمیجی برای حذف یافت نشد.")
        
        return True
    except Exception as e:
        print_error(f"خطا در حذف ایمیج‌های داکر: {e}")
        return False

def remove_project():
    """Remove the entire project"""
    print_header("حذف کامل پروژه")
    
    # Final confirmation
    print_error("⚠️ این عملیات تمام فایل‌های پروژه را حذف خواهد کرد!")
    print_error("⚠️ این عملیات غیرقابل بازگشت است!")
    
    confirm = input("\nآیا از حذف کامل پروژه اطمینان دارید؟ (yes/no): ")
    
    if confirm.lower() != "yes":
        print_info("عملیات حذف لغو شد.")
        return False
    
    try:
        # First try to stop Docker containers if running
        try:
            subprocess.run(["docker-compose", "down"], stderr=subprocess.STDOUT)
        except:
            try:
                subprocess.run(["docker", "compose", "down"], stderr=subprocess.STDOUT)
            except:
                pass
        
        # Get current directory
        current_dir = os.getcwd()
        parent_dir = os.path.dirname(current_dir)
        
        # Remove MySQL data
        try:
            subprocess.run(["rm", "-rf", "/var/lib/mysql/telegram_archive_bot"], stderr=subprocess.STDOUT)
        except:
            pass
        
        print_info("در حال حذف فایل‌ها...")
        
        # Move to parent directory
        os.chdir(parent_dir)
        
        # Remove project directory
        shutil.rmtree(current_dir)
        
        print_success("پروژه با موفقیت حذف شد.")
        return True
    except Exception as e:
        print_error(f"خطا در حذف پروژه: {e}")
        return False

def create_directories():
    """Create required directories"""
    directories = ['logs', 'backups']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print_success(f"دایرکتوری {directory} ایجاد شد.")
        else:
            print_info(f"دایرکتوری {directory} از قبل وجود دارد.")

def start_installation():
    """Start the installation process"""
    print_header("شروع نصب و راه‌اندازی ربات آرشیو تلگرام")
    
    # Create directories
    create_directories()
    
    # Create .env file
    if not create_env_file():
        return False
    
    # Install dependencies
    if not install_dependencies():
        print_error("نصب وابستگی‌ها ناموفق بود. لطفاً مشکل را برطرف کرده و دوباره تلاش کنید.")
        return False
    
    # Ask for Docker
    print("\n")
    print_info("آیا می‌خواهید ربات را با داکر اجرا کنید؟ (اجرای ابدی و خودکار)")
    use_docker = input("(y/n): ")
    
    if use_docker.lower() == 'y':
        # Check Docker installation
        if not check_docker_installed() or not check_docker_compose_installed():
            print_error("داکر یا داکر کامپوز نصب نشده است.")
            print_info("آیا می‌خواهید بدون داکر ادامه دهید؟")
            continue_without_docker = input("(y/n): ")
            
            if continue_without_docker.lower() != 'y':
                return False
            
            # Run without Docker
            return run_without_docker()
        
        # Create Docker files
        create_dockerfile()
        create_docker_compose_file()
        
        # Update .env for Docker
        update_env_for_docker()
        
        # Run with Docker
        return run_with_docker()
    else:
        # Run without Docker
        return run_without_docker()

def main():
    """Main function"""
    while True:
        choice = print_menu()
        
        if choice == "1":
            start_installation()
        elif choice == "2":
            remove_docker_images()
        elif choice == "3":
            if remove_project():
                sys.exit(0)
        elif choice == "0":
            print_info("خروج از برنامه...")
            sys.exit(0)
        else:
            print_error("گزینه نامعتبر! لطفاً دوباره تلاش کنید.")
        
        # Pause before showing menu again
        print("\nبرای ادامه، کلید Enter را فشار دهید...")
        input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_info("\nبرنامه توسط کاربر متوقف شد.")
        sys.exit(0)
    except Exception as e:
        print_error(f"خطای غیرمنتظره: {e}")
        sys.exit(1)

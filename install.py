
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
    
    db_host = input("\n👉 آدرس هاست دیتابیس (پیش‌فرض: localhost): ") or "localhost"
    db_user = input("\n👉 نام کاربری دیتابیس (پیش‌فرض: root): ") or "root"
    db_password = getpass.getpass("\n👉 رمز عبور دیتابیس (پیش‌فرض: ArchiveBot2024!): ") or "ArchiveBot2024!"
    
    with open('.env', 'w') as f:
        f.write(f"BOT_TOKEN={bot_token}\n")
        f.write(f"ADMIN_ID={admin_id}\n")
        f.write(f"DB_HOST={db_host}\n")
        f.write(f"DB_USER={db_user}\n")
        f.write(f"DB_PASSWORD={db_password}\n")
    
    print_success("فایل .env با موفقیت ایجاد شد.")
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

def check_mysql_connection():
    """Check MySQL/MariaDB connection"""
    try:
        # Try to import mysql connector
        import mysql.connector
        print_success("ماژول mysql.connector موجود است.")
        
        # Load env variables
        load_dotenv()
        
        # Try connection
        db_host = os.getenv('DB_HOST', 'localhost')
        db_user = os.getenv('DB_USER', 'root')
        db_password = os.getenv('DB_PASSWORD', 'ArchiveBot2024!')
        
        # Test connection
        try:
            conn = mysql.connector.connect(
                host=db_host,
                user=db_user,
                password=db_password
            )
            conn.close()
            print_success(f"اتصال به دیتابیس با موفقیت انجام شد. (کاربر: {db_user}@{db_host})")
            return True
        except Exception as e:
            print_error(f"خطا در اتصال به دیتابیس: {e}")
            return False
            
    except ImportError:
        print_error("ماژول mysql.connector یافت نشد.")
        return False

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
    """Create docker-compose.yml file"""
    content = """version: '3.8'

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

  db:
    image: mysql:8.0
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: telegram_archive_bot
    volumes:
      - mysql_data:/var/lib/mysql
    ports:
      - "3306:3306"

volumes:
  mysql_data:
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
    """Update .env file for Docker setup"""
    # Load current .env
    load_dotenv()
    
    bot_token = os.getenv('BOT_TOKEN')
    admin_id = os.getenv('ADMIN_ID')
    db_password = os.getenv('DB_PASSWORD')
    
    # Write new .env for Docker
    with open('.env', 'w') as f:
        f.write(f"BOT_TOKEN={bot_token}\n")
        f.write(f"ADMIN_ID={admin_id}\n")
        f.write(f"DB_HOST=db\n")  # Use Docker service name
        f.write(f"DB_USER=root\n")
        f.write(f"DB_PASSWORD={db_password}\n")
    
    print_success("فایل .env برای استفاده با داکر بروزرسانی شد.")

def run_with_docker():
    """Run the application with Docker"""
    print_header("راه‌اندازی با داکر")
    
    try:
        # Build and run with docker-compose
        subprocess.run(["docker-compose", "up", "--build", "-d"], check=True)
        print_success("ربات با موفقیت در داکر راه‌اندازی شد.")
        print_info("برای مشاهده لاگ‌ها از دستور زیر استفاده کنید:")
        print("   docker-compose logs -f bot")
        return True
    except Exception as e:
        print_error(f"خطا در راه‌اندازی داکر: {e}")
        
        # Try alternative command
        try:
            subprocess.run(["docker", "compose", "up", "--build", "-d"], check=True)
            print_success("ربات با موفقیت در داکر راه‌اندازی شد.")
            print_info("برای مشاهده لاگ‌ها از دستور زیر استفاده کنید:")
            print("   docker compose logs -f bot")
            return True
        except Exception as e2:
            print_error(f"خطا در راه‌اندازی داکر با دستور جایگزین: {e2}")
            return False

def run_without_docker():
    """Run the application directly"""
    print_header("راه‌اندازی بدون داکر")
    
    # Check database connection
    if not check_mysql_connection():
        print_info("آیا می‌خواهید MySQL به صورت خودکار نصب شود؟ (فقط برای سیستم‌های لینوکس)")
        install_mysql = input("(y/n): ")
        
        if install_mysql.lower() == 'y':
            try:
                # Try to install MySQL
                subprocess.run(["apt-get", "update"], check=True)
                subprocess.run(["apt-get", "install", "-y", "mysql-server"], check=True)
                subprocess.run(["service", "mysql", "start"], check=True)
                
                # Set root password
                db_password = os.getenv('DB_PASSWORD', 'ArchiveBot2024!')
                subprocess.run([
                    "mysql", "-e", 
                    f"ALTER USER 'root'@'localhost' IDENTIFIED BY '{db_password}';"
                ], check=True)
                
                print_success("MySQL با موفقیت نصب شد.")
            except Exception as e:
                print_error(f"خطا در نصب MySQL: {e}")
                return False
        else:
            print_error("اتصال به دیتابیس برقرار نیست. لطفاً دیتابیس را نصب و پیکربندی کنید.")
            return False
    
    # Create database
    try:
        import mysql.connector
        load_dotenv()
        
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

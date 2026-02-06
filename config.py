import os

class Config:
    # Flask Settings
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    
    # Mail Settings
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME","")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

    # Database Settings
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "123456")
    MYSQL_DB = os.environ.get("MYSQL_DB", "nexovate")
    
    # Aiven/Production specific: SSL mode
    # Set this to "REQUIRED" in your Render environment variables
    MYSQL_SSL_MODE = os.environ.get("MYSQL_SSL_MODE", None)

    # Limiter
    REDIS_URL = os.environ.get("REDIS_URL", "memory://")
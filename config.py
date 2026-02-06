import os

class Config:
    # Flask
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")

    # Database
    MYSQL_HOST = os.environ.get("MYSQL_HOST")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
    MYSQL_DB = os.environ.get("MYSQL_DB")
    MYSQL_SSL_MODE = os.environ.get("MYSQL_SSL_MODE", "REQUIRED")

    # Mail
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

    # Redis/Limiter
    REDIS_URL = os.environ.get("REDIS_URL", "memory://")
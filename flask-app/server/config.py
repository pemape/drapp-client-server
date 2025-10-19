import os
import logging
import sys
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'myjwtsecret'
    LOGIN_RATE_LIMIT = "3 per 10 minutes"

    # Konfigurácia pre JWT v cookies:
    JWT_TOKEN_LOCATION = ['cookies']        # Token sa bude hľadať v cookies
    JWT_COOKIE_SECURE = False               # Nastav na True v produkcii (použitie HTTPS)
    JWT_ACCESS_COOKIE_PATH = '/'            # Cesta, kde je cookie platná
    JWT_COOKIE_CSRF_PROTECT = False         # V produkcii odporúčam povoliť CSRF ochranu, tu pre testovanie False

    # Port configuration
    FLASK_PORT = int(os.environ.get('FLASK_PORT') or 8080)
    MOCK_API_PORT = int(os.environ.get('MOCK_API_PORT') or 5000)

    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    LOG_FORMAT = os.environ.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # Validate log level
    _valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'TRACE']
    if LOG_LEVEL not in _valid_log_levels:
        LOG_LEVEL = 'INFO'
    
    # Convert to logging constants
    LOG_LEVEL_INT = getattr(logging, LOG_LEVEL, logging.INFO)
    
    # Enable trace level if specified
    if LOG_LEVEL == 'TRACE':
        LOG_LEVEL_INT = 5  # Custom trace level
        logging.addLevelName(5, 'TRACE')

    # UPLOAD_FOLDER = "C:\ProgrammingProjects\APPV_DRAI\TP2025_Server-Client_app\flask-app\uploads"
    UPLOAD_FOLDER = f"{os.path.dirname(os.path.abspath(__file__))}/uploads"
    PROCESSING_SERVICE_URL = f"http://0.0.0.0:{MOCK_API_PORT}"
    RECIEVING_ENDPOINT = f"http://localhost:{FLASK_PORT}/photos/processed/recieve"

    @staticmethod
    def setup_logging():
        """Setup logging configuration for the entire application with UTF-8 encoding support"""
        # Get root logger
        root_logger = logging.getLogger()
        
        # Check if logging is already configured to avoid duplicates during Flask reloader
        if root_logger.handlers:
            # If handlers already exist, just return the app logger
            return logging.getLogger('retinal_app')
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(Config.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Clear any existing handlers and set level
        root_logger.handlers.clear()
        root_logger.setLevel(Config.LOG_LEVEL_INT)
        
        # Create formatter
        formatter = logging.Formatter(Config.LOG_FORMAT)
        
        # Create console handler with UTF-8 encoding
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(Config.LOG_LEVEL_INT)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        # Create file handler with UTF-8 encoding
        try:
            file_handler = logging.FileHandler(Config.LOG_FILE, encoding='utf-8')
            file_handler.setLevel(Config.LOG_LEVEL_INT)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            # Log to console if file handler fails
            console_handler.warning(f"Could not create file handler: {e}")
        
        # Disable propagation for specific loggers to prevent duplicates
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(Config.LOG_LEVEL_INT)
        werkzeug_logger.propagate = False
        werkzeug_logger.addHandler(console_handler)
        if 'file_handler' in locals():
            werkzeug_logger.addHandler(file_handler)
        
        # Setup SQLAlchemy logger
        sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
        if Config.LOG_LEVEL == 'DEBUG' or Config.LOG_LEVEL == 'TRACE':
            sqlalchemy_logger.setLevel(logging.INFO)  # Show SQL queries in debug
        else:
            sqlalchemy_logger.setLevel(logging.WARNING)
        sqlalchemy_logger.propagate = False
        sqlalchemy_logger.addHandler(console_handler)
        if 'file_handler' in locals():
            sqlalchemy_logger.addHandler(file_handler)
        
        # Setup custom application logger
        app_logger = logging.getLogger('retinal_app')
        app_logger.setLevel(Config.LOG_LEVEL_INT)
        app_logger.propagate = False
        app_logger.addHandler(console_handler)
        if 'file_handler' in locals():
            app_logger.addHandler(file_handler)
        
        # Setup services loggers
        services_logger = logging.getLogger('server.services')
        services_logger.setLevel(Config.LOG_LEVEL_INT)
        services_logger.propagate = False
        services_logger.addHandler(console_handler)
        if 'file_handler' in locals():
            services_logger.addHandler(file_handler)
        
        return app_logger

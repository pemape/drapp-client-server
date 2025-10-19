from server import create_app
from server.database import db
from server.services.super_admin_service import create_super_admin
from server.config import Config
import logging

# Setup logging before anything else
app_logger = Config.setup_logging()

app = create_app()

def init_admin():
    create_super_admin()
    
def init_process_types():
    from server.services.methods_service import create_default_methods
    create_default_methods()

# Inicializácia databázy v rámci kontextu aplikácie
if __name__ == '__main__': 
    with app.app_context():
        try:
            app_logger.info("Checking and creating tables if necessary...")
            db.create_all()
            init_admin()
            init_process_types()
            app_logger.info("Database initialized successfully.")
        except Exception as e:
            app_logger.error(f"Database initialization error: {e}")

    # Use configurable port from environment variable
    port = Config.FLASK_PORT
    app_logger.info(f"Starting Flask server on port {port} with log level {Config.LOG_LEVEL}")
    app.run(host='0.0.0.0', port=port)
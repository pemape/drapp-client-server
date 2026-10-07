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
    
def init_seed_data():
    from server.services.seed_service import create_seed_data
    create_seed_data()

def init_process_types():
    from server.services.methods_service import create_default_methods
    create_default_methods()

def ensure_schema_columns():
    """Add columns introduced after the initial create_all() (which never alters existing tables)."""
    from sqlalchemy import inspect, text

    # table -> {column: SQL type}
    new_columns = {
        "processed_image_data": {
            "explanation_image_path": "VARCHAR(255)",
            "explanation": "JSON",
        },
    }
    inspector = inspect(db.engine)
    with db.engine.begin() as conn:
        for table, columns in new_columns.items():
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, sql_type in columns.items():
                if name not in existing:
                    app_logger.info(f"Adding missing column {table}.{name}")
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {sql_type}'))

# Inicializácia databázy v rámci kontextu aplikácie
if __name__ == '__main__': 
    with app.app_context():
        try:
            app_logger.info("Checking and creating tables if necessary...")
            db.create_all()
            ensure_schema_columns()
            init_admin()
            init_seed_data()
            init_process_types()
            app_logger.info("Database initialized successfully.")
        except Exception as e:
            app_logger.error(f"Database initialization error: {e}")

    # Use configurable port from environment variable
    port = Config.FLASK_PORT
    app_logger.info(f"Starting Flask server on port {port} with log level {Config.LOG_LEVEL}")
    app.run(host='0.0.0.0', port=port)
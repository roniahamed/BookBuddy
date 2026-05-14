import os
import sys

# Set PYTHONPATH
sys.path.append(os.getcwd())

try:
    from app.main import app
    print("Success: FastAPI app initialized and everything in 'core' is integrated!")
    
    # Check if DB engine is ready
    from app.core.database import engine
    print(f"Database engine: {engine}")
    
    # Check if logging is setup
    from loguru import logger
    logger.info("Verifying integrated logging...")
    
except Exception as e:
    print(f"Error during integration check: {e}")
    import traceback
    traceback.print_exc()

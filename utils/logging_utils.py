import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_info(message: str):
    """Log an info message."""
    logging.info(message)

def log_debug(message: str):
    """Log a debug message."""
    logging.debug(message)

def log_error(message: str, error: Exception = None):
    """Log an error message."""
    logging.error(f"{message}: {error}")

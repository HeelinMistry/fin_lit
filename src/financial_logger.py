import logging
from datetime import datetime
import os  # We'll use this to ensure the log directory exists


def setup_user_output(console_level=logging.INFO, log_directory='logs'):
    """
    Configures logging with a dynamic, month-based filename (YYYY-MM).
    """

    # --- 1. Generate the Dynamic Filename ---

    # Get the current month and year in "YYYY-MM" format
    current_month_str = datetime.now().strftime("%Y-%m")

    # Create the full filename: e.g., 'logs/2026-01.log'
    log_file_path = os.path.join(log_directory, f"{current_month_str}.log")

    # Ensure the log directory exists
    os.makedirs(log_directory, exist_ok=True)

    # --- 2. Standard Logging Setup (Mostly Unchanged) ---

    # Get the root logger and set its minimum level to capture everything
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Define simple format for the console (User Output)
    user_formatter = logging.Formatter('%(message)s')

    # Define detailed format for the file (Audit Trail)
    file_formatter = logging.Formatter(
        '%(message)s',
    )

    # Console Handler (User-facing output)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(user_formatter)
    console_handler.setLevel(console_level)
    root_logger.addHandler(console_handler)

    # File Handler (Complete technical and user output)
    file_handler = logging.FileHandler(log_file_path, mode='a')  # 'a' for append
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(console_level)
    root_logger.addHandler(file_handler)

    # Final check message
    logging.info(f"'{current_month_str}'")

# Call this at the start of your main.py
# setup_user_output()
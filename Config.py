# Config.py

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the Config.py file

LOG_FILE = os.path.join(BASE_DIR, 'app.log')
LOGS_FOLDER = os.path.join(BASE_DIR, 'logs')
AUTO_CLOSE = False  # Set to True if you want the script to close automatically

# Define lists of IP addresses and corresponding ports
DEVICE_IPS = ['192.168.200.80', '192.168.200.85', '192.168.200.143']
DEVICE_PORTS = ['9734', '9734', '9734']
# Add new configuration options for custom date and time range
CUSTOM_DATE_RANGE = False  # Set to True to use a custom date and time range
START_DATE = '2023-01-01 00:00:00'  # Format: 'YYYY-MM-DD HH:MM:SS'
END_DATE = '2023-12-31 23:59:59'    # Format: 'YYYY-MM-DD HH:MM:SS'

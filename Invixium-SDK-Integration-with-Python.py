import clr
import logging
import datetime
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import sys
import requests
import sys

# Load environment variables from the .env file
load_dotenv()

# Define global configuration variables
get_data_from_env = os.getenv("get_data_from_env")
AUTO_CLOSE = os.getenv("AUTO_CLOSE")
insert_into_ERP = os.getenv("insert_into_ERP")
API_ENDPOINT = os.getenv("API_ENDPOINT")
CUSTOM_DATE_RANGE = os.getenv("CUSTOM_DATE_RANGE")
START_DATE = os.getenv("START_DATE")
END_DATE = os.getenv("END_DATE")

# Convert boolean strings to actual booleans
AUTO_CLOSE = AUTO_CLOSE.lower() == "true"
get_data_from_env = int(get_data_from_env)
insert_into_ERP = insert_into_ERP.lower() == "true"
CUSTOM_DATE_RANGE = CUSTOM_DATE_RANGE.lower() == "true"

# Check if data should be retrieved from environment variables or user input
if get_data_from_env == 1:
    DEVICE_IPS = os.getenv("DEVICE_IPS").split(",")
    DEVICE_PORTS = os.getenv("DEVICE_PORTS").split(",")
elif get_data_from_env == 0:
    print("Please enter the IP addresses and ports of the devices you want to connect to from the system.")
    exit(1)

# Add references to the required DLL files
clr.AddReference('System')
dll_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SDK')
clr.AddReference(os.path.join(dll_folder, 'Newtonsoft.Json.dll'))
clr.AddReference(os.path.join(dll_folder, 'IXMDemo.Common.dll'))
clr.AddReference(os.path.join(dll_folder, 'IXMSoft.Business.Managers.dll'))
clr.AddReference(os.path.join(dll_folder, 'IXMSoft.Business.SDK.dll'))
clr.AddReference(os.path.join(dll_folder, 'IXMSoft.Common.Models.dll'))
clr.AddReference(os.path.join(dll_folder, 'IXMSoft.Data.DataAccess.dll'))

from System import DateTime
from IXMSoft.Common.Models import TransactionLogArg, TransactionLog, Device
from IXMSoft.Business.SDK import *
from IXMSoft.Business.SDK.Data import DeviceConnectionType, TransactionLogEventType
from IXMSoft.Business.SDK import NetworkConnection, TransactionLogManager

@dataclass
class DeviceConfig:
    IP: str
    port: int

@dataclass
class TransactionLogData:
    UserRecordId: str
    check_date: str
    check_time: str

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get the directory of the Config.py file
LOG_FILE = os.path.join(BASE_DIR, 'app.log')
LOGS_FOLDER = os.path.join(BASE_DIR, 'logs')

# Configure logging
log_file_path = os.path.join(LOGS_FOLDER, 'app.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO,format='%(asctime)s - %(levelname)s - %(message)s')

# Function to check the status of a device
def check_device_status(device):
    try:
        response = os.system(f"ping {device.IPaddress} -n 1")
        is_connected = response == 0
        network_status = "Connected" if is_connected else "Not Connected"

        if is_connected:
            # Attempt to connect to the device's IP and port
            conn = NetworkConnection(device)
            conn.OpenConnection()
            conn.CloseConnection()
            logging.info(f"Successfully connected to {device.IPaddress}:{device.Port}")
        else:
            logging.warning(f"Could not connect to {device.IPaddress}:{device.Port}")

        logging.info(f"Network Status: {network_status}")

        return is_connected
    except Exception as ex:
        logging.error(f"Error checking device status: {ex}")
        return False

# Function to create a log folder with a timestamp
def create_log_folder(ip_address):
    timestamp = datetime.datetime.now()
    folder_name = f"{ip_address}_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}"
    log_folder_path = os.path.join(LOGS_FOLDER, folder_name)
    os.makedirs(log_folder_path, exist_ok=True)
    return log_folder_path

# Function to create a text log file for transaction logs
def create_txt_log_file(log_folder, logs):
    txt_log_file_name = "transaction_logs.txt"  # Adjust the desired name for the txt file
    txt_log_file_path = os.path.join(log_folder, txt_log_file_name)

    with open(txt_log_file_path, 'a') as writer:
        writer.write(f"{'-' * 5}({datetime.datetime.now()}){'-' * 5}\n")
        for log in logs:
            writer.write(f"{log.UserRecordId};{log.check_date};{log.check_time}\n")

# Function to create an application log file
def create_log_app_file(log_folder, device, additional_info=None):
    log_app_file_name = f"{device.IPaddress}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    log_app_file_path = os.path.join(log_folder, log_app_file_name)

    with open(log_app_file_path, 'a') as app_writer:
        app_writer.write(f"{'-' * 5}({datetime.datetime.now()}){'-' * 5}\n")
        app_writer.write(f"{datetime.datetime.now()} - INFO - Successfully connected to {device.IPaddress}:{device.Port}\n")
        if additional_info:
            app_writer.write(f"{datetime.datetime.now()} - INFO - {additional_info}\n")

# Function to retrieve transaction logs
def get_transaction_logs(conn, device, start_date, end_date):
    transaction_log_arguments = TransactionLogArg()
    transaction_log_arguments.StartDate = start_date
    transaction_log_arguments.EndDate = end_date

    transaction_logs = []
    try:
        log_manager = TransactionLogManager(conn)

        all_log_counter = log_manager.GetAllDateWiseTransactionLogCount(
            transaction_log_arguments.StartDate, transaction_log_arguments.EndDate)

        for i in range(0, all_log_counter, 100):
            transaction_log_arguments.StartCounter = i
            transaction_log_arguments.EndCounter = i + 100
            logs_batch = log_manager.GetDateWiseTransactionLog(transaction_log_arguments)

            for item in logs_batch:
                if item.EventType == TransactionLogEventType.Authentication:
                    log_data = TransactionLogData(
                        UserRecordId=item.UserId if item.UserId else None,
                        check_date=item.Date.ToShortDateString(),
                        check_time=item.Time
                    )
                    transaction_logs.append(log_data)

    except Exception as ex:
        logging.error(f"Error retrieving transaction logs: {ex}")
        conn.CloseConnection()
        conn.Dispose()
        create_log_app_file(device, f"Error retrieving transaction logs: {ex}")

    return transaction_logs

# Function to set up a device
def setup_device(ip_address, port):
    device = Device()
    device.IPaddress = ip_address
    device.Port = port
    device.ConnectionType = DeviceConnectionType.Ethernet

    is_connected = check_device_status(device)
    network_status = "Connected" if is_connected else "Not Connected"
    logging.info(f"Network Status: {network_status}")

    return device

# Function to post a log to ERP
def post_log_to_ERP(log, device):
    data = {
        'user_id': log.UserRecordId,
        "check_date": log.check_date,
        "check_time": log.check_time
    }

    try:
        r = requests.post(url=API_ENDPOINT, data=data)
        print("The response is:%s" % r.text)
    except Exception as ex:
        print(f"Error posting log to ERP: {ex}")

# Main function to orchestrate the entire process
def main():
    start_time = datetime.datetime.now()
    logging.info(f"{'-' * 5}Script started at {start_time}{'-' * 5}")

    if not os.path.exists(LOGS_FOLDER):
        os.makedirs(LOGS_FOLDER)

    if CUSTOM_DATE_RANGE:
        # Parse custom start and end dates from the configuration file
        start_date = datetime.datetime.strptime(START_DATE, '%Y-%m-%d %H:%M:%S')
        end_date = datetime.datetime.strptime(END_DATE, '%Y-%m-%d %H:%M:%S')
    else:
        # Use the previous logic to calculate the date and time range
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=1)

    start_date_dotnet = DateTime(start_date.year, start_date.month, start_date.day, start_date.hour, start_date.minute, start_date.second)
    end_date_dotnet = DateTime(end_date.year, end_date.month, end_date.day, end_date.hour, end_date.minute, end_date.second)

    # Create an empty list to store logs
    all_logs = []

    # Iterate through both lists of IP addresses and ports
    for ip_address, port in zip(DEVICE_IPS, DEVICE_PORTS):
        device = setup_device(ip_address, port)
        if check_device_status(device):
            conn = NetworkConnection(device)
            try:
                conn.OpenConnection()
                logs = get_transaction_logs(conn, device, start_date_dotnet, end_date_dotnet)
                conn.CloseConnection()
                # Append the logs to the list
                all_logs.extend(logs)
            except requests.ConnectionError as api_error:
                # Handle the API connection error
                logging.error(f"API Connection Error: {api_error}")
                sys.exit(1)  # Exit the script with a non-zero exit code
            except Exception as ex:
                logging.error(f"Error in main function: {ex}", exc_info=True)

            # Create a log folder for the IP address with timestamp
            log_folder = create_log_folder(ip_address)
            # Create a log file for the retrieved logs
            create_txt_log_file(log_folder, logs)
            # Create the app.log file within the same folder
            create_log_app_file(log_folder, device)

    # Check if insert_into_ERP is True and then post the logs to ERP
    if insert_into_ERP:
        for log in all_logs:
            post_log_to_ERP(log, device)

    end_time = datetime.datetime.now()
    logging.info(f"{'-' * 5}Script finished at {end_time}{'-' * 5}")
    logging.info(f"Total execution time: {end_time - start_time}")

    if not AUTO_CLOSE:
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()

import clr
import logging
import datetime
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import sys

# Load environment variables from .env file
load_dotenv()

# Check the value of get_data_fromTXTfile
get_data_fromTXTfile = os.environ.get("get_data_fromTXTfile", "1")

if get_data_fromTXTfile == "1":
    # Import values from the configuration file
    import Config
else:
    # Values are not set in the configuration file, use default values
    from dataclasses import dataclass

@dataclass
class DeviceConfig:
    IP: str
    port: int

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
class TransactionLogData:
    UserRecordId: str
    check_date: str
    check_time: str

# Configure logging
log_file_path = os.path.join(Config.LOGS_FOLDER, 'app.log')
logging.basicConfig(filename=log_file_path, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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

# Modify the get_transaction_logs function to accept the device parameter
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

    return transaction_logs

def setup_device(ip_address, port):
    device = Device()
    device.IPaddress = ip_address
    device.Port = port
    device.ConnectionType = DeviceConnectionType.Ethernet

    is_connected = check_device_status(device)
    network_status = "Connected" if is_connected else "Not Connected"
    logging.info(f"Network Status: {network_status}")

    return device

def print_logs(logs):
    for log in logs:
        print(f"UserRecordId: {log.UserRecordId}, Check Date: {log.check_date}, Check Time: {log.check_time}")

def main():
    start_time = datetime.datetime.now()
    logging.info(f"Script started at {start_time}")

    if not os.path.exists(Config.LOGS_FOLDER):
        os.makedirs(Config.LOGS_FOLDER)

    if Config.CUSTOM_DATE_RANGE:
        # Parse custom start and end dates from the configuration file
        start_date = datetime.datetime.strptime(Config.START_DATE, '%Y-%m-%d %H:%M:%S')
        end_date = datetime.datetime.strptime(Config.END_DATE, '%Y-%m-%d %H:%M:%S')
    else:
        # Use the previous logic to calculate the date and time range
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=1)

    start_date_dotnet = DateTime(start_date.year, start_date.month, start_date.day,
                                 start_date.hour, start_date.minute, start_date.second)
    end_date_dotnet = DateTime(end_date.year, end_date.month, end_date.day,
                               end_date.hour, end_date.minute, end_date.second)

    # Iterate through both lists of IP addresses and ports
    for ip_address, port in zip(Config.DEVICE_IPS, Config.DEVICE_PORTS):
        device = setup_device(ip_address, port)
        if check_device_status(device):
            conn = NetworkConnection(device)
            try:
                conn.OpenConnection()
                logs = get_transaction_logs(conn, device, start_date_dotnet, end_date_dotnet)
                log_file_name = f"{ip_address}_{port}_{end_date.strftime('%d_%m_%Y_%H_%M_%S')}.txt"
                log_file_path = os.path.join(Config.LOGS_FOLDER, log_file_name)

                with open(log_file_path, 'w') as writer:
                    for log in logs:
                        writer.write(f"{log.UserRecordId};{log.check_date};{log.check_time}\n")

                # Log the return values
                logging.info(f"DeviceConfig: {device}")
                logging.info(f"TransactionLogData: {logs}")
            except Exception as ex:
                logging.error(f"Error in main function: {ex}", exc_info=True)
            finally:
                conn.CloseConnection()

    end_time = datetime.datetime.now()
    logging.info(f"Script finished at {end_time}")
    logging.info(f"Total execution time: {end_time - start_time}")

    if not Config.AUTO_CLOSE:
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()

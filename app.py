import time
import os
import yaml
import requests
import math
import sys # For sys.exit()
import board # from adafruit-blinka
import busio # from adafruit-blinka
import adafruit_mpu6050
from adafruit_mpu6050 import Range as MPU6050_Range # For accelerometer range setting

REQUIRED_SECTIONS = {
    'MPUSettings': ['i2c_address', 'knock_threshold', 'accelerometer_range'],
    'NetworkSettings': ['target_host', 'target_port', 'endpoint'],
    'TimingSettings': ['debounce_time_seconds'],
    'GeneralSettings': ['safe_mode']
}

CONFIG_FILE_NAME = 'config.yaml'

def load_config():
    if not os.path.exists(CONFIG_FILE_NAME):
        print(f"ERROR: Configuration file '{CONFIG_FILE_NAME}' not found.")
        print("Please create it. You can use the following as a template:")
        template = {section: {key: "(value)" for key in keys} for section, keys in REQUIRED_SECTIONS.items()}
        template['MPUSettings']['i2c_address'] = "0x68" # Default MPU6050 address
        template['MPUSettings']['knock_threshold'] = 20.0
        template['MPUSettings']['accelerometer_range'] = "RANGE_2_G"
        template['NetworkSettings']['target_host'] = "your_host_here"
        template['NetworkSettings']['target_port'] = 5000
        template['NetworkSettings']['endpoint'] = "/your_endpoint"
        template['TimingSettings']['debounce_time_seconds'] = 1.5
        template['GeneralSettings']['safe_mode'] = True
        print("---")
        print(yaml.dump(template, sort_keys=False))
        print("---")
        sys.exit(1)

    try:
        with open(CONFIG_FILE_NAME, 'r') as f:
            config = yaml.safe_load(f)
            if config is None:
                print(f"ERROR: Configuration file '{CONFIG_FILE_NAME}' is empty.")
                sys.exit(1)
    except yaml.YAMLError as e:
        print(f"ERROR: Could not parse '{CONFIG_FILE_NAME}': {e}")
        sys.exit(1)
    except IOError as e:
        print(f"ERROR: Could not read '{CONFIG_FILE_NAME}': {e}")
        sys.exit(1)

    missing_keys = []
    for section, keys in REQUIRED_SECTIONS.items():
        if section not in config:
            missing_keys.append(f"Section '{section}' is missing.")
            continue
        if not isinstance(config[section], dict):
            missing_keys.append(f"Section '{section}' is not correctly formatted (should be a dictionary).")
            continue
        for key in keys:
            if key not in config[section]:
                missing_keys.append(f"Key '{key}' in section '{section}' is missing.")

    if missing_keys:
        print(f"ERROR: Configuration file '{CONFIG_FILE_NAME}' is missing required settings:")
        for item in missing_keys:
            print(f"  - {item}")
        sys.exit(1)
    
    print(f"Configuration successfully loaded from: '{os.path.abspath(CONFIG_FILE_NAME)}'")
    return config

config = load_config()

mpu_settings = config['MPUSettings']
I2C_ADDRESS = int(mpu_settings['i2c_address']) # Note: int() handles '0x' prefixed hex strings
KNOCK_THRESHOLD = float(mpu_settings['knock_threshold'])
ACCEL_RANGE_STR = str(mpu_settings['accelerometer_range']).upper()

# Mapping for human-readable range names to library constants
ACCEL_RANGE_MAP = {
    "RANGE_2_G": MPU6050_Range.RANGE_2_G,
    "RANGE_4_G": MPU6050_Range.RANGE_4_G,
    "RANGE_8_G": MPU6050_Range.RANGE_8_G,
    "RANGE_16_G": MPU6050_Range.RANGE_16_G,
}
if ACCEL_RANGE_STR not in ACCEL_RANGE_MAP:
    print(f"ERROR: Invalid 'accelerometer_range' in config: '{ACCEL_RANGE_STR}'.")
    print(f"Valid values are: {', '.join(ACCEL_RANGE_MAP.keys())}")
    sys.exit(1)
MPU_ACCEL_RANGE = ACCEL_RANGE_MAP[ACCEL_RANGE_STR]

network_settings = config['NetworkSettings']
TARGET_HOST = str(network_settings['target_host'])
TARGET_PORT = int(network_settings['target_port'])
ENDPOINT = str(network_settings['endpoint'])
FULL_TARGET_URL = f"http://{TARGET_HOST}:{TARGET_PORT}{ENDPOINT}"

timing_settings = config['TimingSettings']
DEBOUNCE_TIME = float(timing_settings['debounce_time_seconds'])

general_settings = config['GeneralSettings']
SAFE_MODE = bool(general_settings['safe_mode'])

last_detection_time = 0 # Used for debouncing knock detections

def send_post_request():
    global last_detection_time
    current_time = time.time()

    if (current_time - last_detection_time) < DEBOUNCE_TIME:
        return

    print(f"Significant motion detected at {time.strftime('%Y-%m-%d %H:%M:%S')}!")
    last_detection_time = current_time

    if SAFE_MODE:
        print(f"[SAFE MODE] Would send POST to {FULL_TARGET_URL}")
        return

    try:
        response = requests.post(FULL_TARGET_URL)
        print(f"POST request sent to {FULL_TARGET_URL}. Status: {response.status_code}")
        if 200 <= response.status_code < 300:
            print("Request successful.")
        else:
            print(f"Request failed. Response content: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending POST request to {FULL_TARGET_URL}: {e}")

def main():
    print("Starting MPU-6050 knock detector...")
    if SAFE_MODE:
        print("*** RUNNING IN SAFE MODE - NO ACTUAL POST REQUESTS WILL BE SENT ***")
    print(f"Target URL: {FULL_TARGET_URL}")
    print(f"Knock Threshold: {KNOCK_THRESHOLD} m/s^2 (on any axis)")
    print(f"Accelerometer Range: {ACCEL_RANGE_STR}")
    print(f"Debounce Time: {DEBOUNCE_TIME}s")
    print(f"MPU6050 I2C Address: {hex(I2C_ADDRESS)}")

    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        mpu = adafruit_mpu6050.MPU6050(i2c, address=I2C_ADDRESS)
        mpu.accelerometer_range = MPU_ACCEL_RANGE
        print("MPU-6050 initialized successfully.")

    except ValueError as e:
        print(f"Error initializing MPU-6050: {e}")
        print("Please check I2C wiring, address, and ensure I2C is enabled on the Pi.")
        if "No I2C device at address" in str(e) or "Could not find I2C device" in str(e) :
             print(f"Run 'sudo i2cdetect -y 1' to check for devices at {hex(I2C_ADDRESS)}.") # This is a common issue
        return
    except RuntimeError as e:
        print(f"Runtime error initializing MPU-6050: {e}")
        print("This might be due to a problem with the I2C bus or permissions.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during MPU-6050 initialization: {e}")
        return

    print("Monitoring for knocks...")
    while True:
        try:
            ax, ay, az = mpu.acceleration # m/s^2 units from the library

            if abs(ax) > KNOCK_THRESHOLD or \
               abs(ay) > KNOCK_THRESHOLD or \
               abs(az) > KNOCK_THRESHOLD:
                # print(f"Threshold exceeded: X={ax:6.2f} Y={ay:6.2f} Z={az:6.2f}") # Could be noisy, uncomment for fine-tuning
                send_post_request()

            time.sleep(0.02) # Balance responsiveness with CPU/I2C load

        except OSError as e:
            print(f"OSError during MPU read: {e}. Re-initializing I2C might be needed or check connection.")
            time.sleep(1) # Give it a moment before trying again
        except Exception as e:
            print(f"An unexpected error occurred in the loop: {e}")
            time.sleep(1)

if __name__ == "__main__":
    main() 
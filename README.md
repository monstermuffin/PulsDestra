# PulsDestra

_PulsDestra:_ "Pulsare" - Latin, to knock. "Fenestra" - Latin, window.

PulsDestra allows the toggling of the liked status of the currently playing song on a MeloDestra display by tapping/knocking the frame. It uses an MPU-6050 accelerometer to detect knocks and sends a POST request to MeloDestra.

## How it Works
The PulsDestra app/script uses an MPU-6050 accelerometer connected to a Raspberry Pi (or similar device). The app continuously monitors the accelerometer for sharp movements (knocks). When a knock exceeding a defined threshold is detected, a HTTP POST request is sent to a specified URL. This URL can be configured to anything you want, by default for use with MeloDestra it's `/toggle-like`.

The script includes a debounce mechanism to prevent multiple POST requests from a single knock which also functions as a cooldown period. 

Safemode is also configurable with `safe_mode`. When safemode is enabled, the app will log detected knocks and intended POST actions to the console without actually sending any network requests. This is useful for testing the `knock_threshold`.


## Configuration
`config.yaml` is the configuration file for PulsDestra. You can use the template provided in the repo but ensure to change the settings to suit your needs.
Key configuration options:

*   **`MPUSettings`**:
    *   `i2c_address`: The I2C address of your MPU-6050 (usually `0x68`).
    *   `knock_threshold`: The minimum acceleration magnitude (m/s²) on any axis to register as a knock. You'll need to experiment to find a good value (e.g., 10.0-30.0).
    *   `accelerometer_range`: The measurement range of the accelerometer (e.g., `RANGE_2_G`, `RANGE_4_G`, `RANGE_8_G`, `RANGE_16_G`). `RANGE_2_G` is sufficient for detecting knocks. This is the only mode I have really tested with as it's all I required for this use case.
*   **`NetworkSettings`**:
    *   `target_host`: The IP address or hostname of your MeloDestra device.
    *   `target_port`: The port number for the MeloDestra API.
    *   `endpoint`: The specific API endpoint to trigger the like/unlike action (e.g., `/toggle-like`).
*   **`TimingSettings`**:
    *   `debounce_time_seconds`: The minimum time (in seconds) to wait after a detected knock before processing another one.
*   **`GeneralSettings`**:
    *   `safe_mode`: Set to `true` to log detected knocks and intended POST actions to the console without actually sending any network requests. Set to `false` for normal operation.

**Example `config.yaml`:**

```yaml
MPUSettings:
  i2c_address: 0x68
  knock_threshold: 12.0
  accelerometer_range: "RANGE_2_G"
NetworkSettings:
  target_host: "ip/hostname"
  target_port: 5000
  endpoint: "/toggle-like"
TimingSettings:
  debounce_time_seconds: 5.0
GeneralSettings:
  safe_mode: false
```

## Setup
-  **Hardware:**
    *   Connect your MPU-6050 to your Raspberry Pi's I2C pins.
        *   SCL to GPIO (typically GPIO3, Pin 5 on Raspberry Pi)
        *   SDA to GPIO (typically GPIO2, Pin 3 on Raspberry Pi)
        *   VCC to 3.3V or 5V (check MPU-6050 module specs - 3.3v is usual but some boards can take 5v)
        *   GND to GND
    *   Ensure I2C is enabled on your Raspberry Pi:
        *   Run `sudo raspi-config`.
        *   Navigate to `Interface Options` -> `I2C`.
        *   Enable I2C and exit `raspi-config`.
        *   Reboot.
    *   Verify the MPU-6050 is detected by running `sudo i2cdetect -y 1` (the address, usually `68`, should appear).

-  **GPIO Permissions:**
    *   For Raspbian, you need to add your user to the `gpio` group to access GPIO without requiring `sudo`:
        ```bash
        sudo usermod -a -G gpio $USER
        ```
    *   You also need to add your user to the `i2c` group to access I2C devices like the MPU-6050:
        ```bash
        sudo usermod -a -G i2c $USER
        ```
    *   After running these commands, **log out and log back in** (or reboot) for the group changes to take effect.

> [!TIP]
> You can run the application with `sudo python app.py` as an alternative, but adding to the gpio and i2c groups is the recommended approach.

-  **Software Dependencies:**
    *   Clone this repository or download the files.
        ```bash
        git clone https://github.com/monstermuffin/PulsDestra.git
        cd PulsDestra
        ```
    *   Install system dependencies (required for building Python packages):
        ```bash
        sudo apt update
        sudo apt install swig liblgpio-dev build-essential python3-dev
        ```
    *   Use a Python venv:
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```
    *   Install the required Python libraries:
        ```bash
        pip install -r requirements.txt
        ```

> [!NOTE]
> The requirements include both `RPi.GPIO` (for Pi models prior to 5) and `lgpio`/`rpi-lgpio` (for Pi 5+). The system dependencies (`swig` and `liblgpio-dev`) are needed to build the `lgpio` Python package from source.

-  **Configuration:**
    *   Create and customize your `config.yaml` file as described above.

## Running the Application
-  Activate the venv:
    ```bash
    source .venv/bin/activate
    ```
-  Run the app:
    ```bash
    python app.py
    ```

PulsDestra will print status messages, including whether it's in safe mode, the target URL, and initialization status of the MPU-6050. It will then start monitoring for knocks.

## Tuning Knock Threshold
At this point you should be able to knock the surface where the sensor is and tune the `knock_threshold` in the config file until you get the desired sensitivity. 

If the log is continuously spammed with `Knock detected too soon. Debounced` then you need to increase the `knock_threshold`. Keep increasing the threshold until you must trigger a knock yourself for the app to register it. 

> [!TIP]
> Start with a `knock_threshold` around 10-15 for gentle taps, or 20-30 for firmer knocks. Adjust based on your setup and sensitivity preferences.

> [!WARNING]
> If you see continuous "Knock detected too soon. Debounced" messages, increase the `knock_threshold` value to reduce false positives.

## Running as a System Service

### Automated Service Setup

- **Run the setup script:**
   ```bash
   ./setup_service.sh
   ```

This script will:
- Add your user to the `gpio` and `i2c` groups (if not already done).
- Create a systemd service file with the correct user and paths.
- Install and enable the service for automatic startup.
- Provide you with service management commands.

- **Start the service:**
   ```bash
   sudo systemctl start pulsedestra
   ```
   
> [!IMPORTANT]
> Run the script as your regular user (without `sudo`). The script will prompt for sudo password when needed for system operations, but needs to detect your actual username correctly.

> [!IMPORTANT]
> After running the setup script, you must **log out and log back in** (or reboot) for the group permissions to take effect.

### Manual Service Setup

If you prefer to set up the service manually or the script doesn't work for your setup:

- Create the service file at `/etc/systemd/system/pulsedestra.service`:
   ```ini
   [Unit]
   Description=PulsDestra
   After=network.target

   [Service]
   Type=simple
   User=YOUR_USERNAME
   Group=YOUR_USERNAME
   WorkingDirectory=/path/to/your/PulsDestra
   Environment=PATH=/path/to/your/PulsDestra/.venv/bin
   Environment=PYTHONUNBUFFERED=1
   ExecStart=/path/to/your/PulsDestra/.venv/bin/python /path/to/your/PulsDestra/app.py
   Restart=always
   RestartSec=10
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   ```

- Replace `YOUR_USERNAME` and `/path/to/your/PulsDestra` with your actual username and installation path.

- Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable pulsedestra
   sudo systemctl start pulsedestra
   ```

### Service Management Commands

Manage the service with the following commands:

- **Start the service:** `sudo systemctl start pulsedestra`
- **Stop the service:** `sudo systemctl stop pulsedestra`
- **Check service status:** `sudo systemctl status pulsedestra`
- **View service logs:** `sudo journalctl -u pulsedestra -f`
- **Disable auto-start:** `sudo systemctl disable pulsedestra`
- **Enable auto-start:** `sudo systemctl enable pulsedestra`
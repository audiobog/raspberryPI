### Raspberry Pi 5 with Ubuntu Desktop, BME680, Prometheus, and Grafana

This guide provides a setup for a Raspberry Pi 5 running Ubuntu Desktop, a BME680 breakout sensor, and a full monitoring stack using Prometheus and Grafana.

### 1\. Hardware Setup

First, connect the BME680 breakout board to your Raspberry Pi 5's GPIO pins. The sensor uses the **I²C protocol**.

| BME680 Pin | Raspberry Pi 5 GPIO Pin | Purpose |
| :--- | :--- | :--- |
| **VIN** | **Pin 1 (3.3V)** | Power (3.3V) |
| **GND** | **Pin 9 (GND)** | Ground |
| **SDA** | **Pin 3 (SDA)** | I²C Data Line |
| **SCL** | **Pin 5 (SCL)** | I²C Clock Line |

### 2\. Operating System and Basic Configuration

1.  **Install Ubuntu Desktop**: Use the **Raspberry Pi Imager** to flash the latest 64-bit Ubuntu Desktop image to your microSD card or SSD.

2.  **Enable I²C**: Open a terminal and run `sudo raspi-config`. Navigate to `Interfacing Options` -\> `I2C` and enable it.

3.  **Grant User Permissions**: For your user to access the GPIO and I2C hardware, you must add them to the `gpio` and `i2c` groups. These groups may not exist by default on Ubuntu, so you may need to create them.

    ```bash
    # Check if groups exist (optional)
    getent group gpio i2c

    # If they don't exist, create them
    sudo groupadd gpio
    sudo groupadd i2c

    # Add your user to the groups
    sudo usermod -a -G gpio,i2c $USER

    # Create a udev rule for GPIO permissions
    sudo nano /etc/udev/rules.d/99-gpio.rules
    ```

    Add the following content to the udev file:

    ```
    SUBSYSTEM=="gpio", GROUP="gpio", MODE="0660"
    SUBSYSTEM=="gpiochip", GROUP="gpio", MODE="0660"
    ```

    Reboot the system for changes to take effect: `sudo reboot`

### 3\. Prometheus Exporter Script

The core of the setup is a Python script that reads data from the BME680 sensor and exposes it in a format Prometheus can understand. This requires a **virtual environment** to manage Python packages securely.

1.  **Create and Activate Virtual Environment**:

    ```bash
    sudo apt install python3-venv
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install Python Libraries**:

    ```bash
    pip install adafruit-circuitpython-bme680 adafruit-bus-device prometheus_client
    ```

3.  **Create the Exporter Script**: Create a file named `bme680_exporter.py` with the following code. This script will run a web server on port `9100` that Prometheus can scrape.

    ```python
    import time
    import board
    import adafruit_bme680
    from prometheus_client import start_http_server, Gauge

    TEMPERATURE = Gauge('bme680_temperature_celsius', 'Temperature reading in Celsius')
    HUMIDITY = Gauge('bme680_humidity_percent', 'Humidity reading in percent')
    PRESSURE = Gauge('bme680_pressure_hpa', 'Pressure reading in hectopascals')
    GAS_RESISTANCE = Gauge('bme680_gas_resistance_ohms', 'Gas resistance reading in Ohms')
    ALTITUDE = Gauge('bme680_altitude_meters', 'Altitude reading in meters')

    i2c = board.I2C()
    bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x76)
    bme680.sea_level_pressure = 1013.25

    start_http_server(9100)
    print("Prometheus exporter started on port 9100...")

    while True:
        TEMPERATURE.set(bme680.temperature)
        HUMIDITY.set(bme680.relative_humidity)
        PRESSURE.set(bme680.pressure)
        GAS_RESISTANCE.set(bme680.gas)
        ALTITUDE.set(bme680.altitude)
        time.sleep(10)
    ```

4.  **Run the Script**:

    ```bash
    python3 bme680_exporter.py
    ```

### 4\. Prometheus and Grafana Setup

Prometheus and Grafana are lightweight enough to run on the Pi and provide a powerful monitoring and visualization platform.

1.  **Install Prometheus**: Download the `linux-arm64` binary from the [Prometheus website](https://prometheus.io/download/) or compile it from source.

    ```bash
    # (Skip if you downloaded the binary)
    sudo apt install -y git build-essential golang
    git clone https://github.com/prometheus/prometheus.git
    cd prometheus && make build
    ```

    Then, create the Prometheus user and directories, move the binaries, and create a systemd service file to run it.

2.  **Configure Prometheus**: Edit `/etc/prometheus/prometheus.yml` to add a new `scrape_configs` job that points to your Python exporter script.

    ```yaml
    scrape_configs:
      - job_name: "bme680_sensor"
        static_configs:
          - targets: ["localhost:9100"]
    ```

    Reload the Prometheus service to apply the changes: `sudo systemctl reload prometheus`

3.  **Install Grafana**: Add the Grafana APT repository and install it with `apt`.

    ```bash
    sudo apt-get install -y apt-transport-https software-properties-common wget
    wget -q -O - https://packages.grafana.com/gpg.key | gpg --dearmor | sudo tee /usr/share/keyrings/grafana.gpg > /dev/null
    echo "deb [signed-by=/usr/share/keyrings/grafana.gpg] https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
    sudo apt-get update
    sudo apt-get install grafana
    sudo systemctl enable --now grafana-server
    ```

4.  **Access Grafana**: Navigate to `http://<your-pi-ip>:3000` in a web browser. The default login is **`admin`** / **`admin`**.

5.  **Add a Prometheus Data Source**: In Grafana, go to **Connections** -\> **Add new connection** -\> **Prometheus**. Point the URL to your local Prometheus server: `http://localhost:9090`.

6.  **Create a Dashboard**: Build a new dashboard and create panels to visualize your BME680 data using the PromQL query language (e.g., `bme680_temperature_celsius`).

# TODO
Make the python script start automatically on reboot. (as a service)
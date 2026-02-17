# UniSat Payload Modules

Swappable payload modules for different mission types.

## Available Payloads

| Payload | Description | Sensor |
|---------|-------------|--------|
| **radiation_monitor** | Geiger counter dosimeter | SBM-20 |
| **earth_observation** | Multispectral camera | IMX219 + filters |
| **iot_relay** | IoT message relay | LoRa SX1276 |
| **magnetometer_survey** | Magnetic field mapping | LIS3MDL (high-res) |
| **spectrometer** | Optical spectrometer | AS7265x |

## Creating a Custom Payload

1. Create a new directory under `payloads/`
2. Implement `PayloadInterface` from `payload_interface.py`
3. Add a `config.json` with default parameters
4. Register in `mission_config.json`

```python
from payloads.payload_interface import PayloadInterface, PayloadSample

class MyPayload(PayloadInterface):
    def initialize(self) -> bool:
        # Setup your sensor hardware
        return True

    def collect_sample(self) -> PayloadSample:
        # Read sensor and return data
        return PayloadSample(...)

    def shutdown(self) -> None:
        # Power down sensor
        pass
```

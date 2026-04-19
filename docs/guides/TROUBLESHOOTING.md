# UniSat Troubleshooting Guide

Common issues and solutions for building, running, and debugging the UniSat CubeSat platform.

---

## Build Errors

### CMake: ARM toolchain not found

**Symptom:** `WARNING: ARM toolchain not found, building for host (test mode)`

**Cause:** `arm-none-eabi-gcc` is not in your PATH.

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install gcc-arm-none-eabi

# macOS
brew install --cask gcc-arm-embedded

# Windows — download from https://developer.arm.com/downloads/-/gnu-rm
# Add the bin/ directory to your PATH
```

After installing, verify: `arm-none-eabi-gcc --version`

### CMake: build fails on FreeRTOS headers

**Symptom:** `fatal error: cmsis_os2.h: No such file or directory`

**Cause:** FreeRTOS and CMSIS-RTOS2 headers are not included in the base repo. The firmware expects STM32CubeMX-generated middleware.

**Solution:**
1. Generate the project with STM32CubeMX for STM32F446RE with FreeRTOS enabled.
2. Copy the `Middlewares/` directory into `firmware/stm32/`.
3. Add the include path to `CMakeLists.txt`:
   ```cmake
   include_directories(stm32/Middlewares/Third_Party/FreeRTOS/Source/include)
   ```

Alternatively, build in simulation mode (host build) which skips FreeRTOS:
```bash
cd firmware && mkdir build && cd build
cmake .. && make
```
The `SIMULATION_MODE` define is set automatically when the ARM toolchain is absent.

### pip install fails for `sgp4`

**Symptom:** `error: Microsoft Visual C++ 14.0 or greater is required` (Windows)

**Solution:** The `sgp4` package includes C extensions. Install Build Tools for Visual Studio, or use a pre-built wheel:
```bash
pip install sgp4 --only-binary=:all:
```

### pip install fails for `aiofiles`

**Symptom:** `ModuleNotFoundError: No module named 'aiofiles'`

**Solution:** This dependency is required by the flight-software DataLogger:
```bash
cd flight-software
pip install -r requirements.txt
```

---

## Runtime Errors

### Serial port permission denied (Linux)

**Symptom:** `serial.serialutil.SerialException: [Errno 13] could not open port /dev/ttyS0: [Errno 13] Permission denied`

**Solution:**
```bash
# Add your user to the dialout group
sudo usermod -aG dialout $USER
# Log out and back in, then verify
groups | grep dialout
```

### Serial port not found

**Symptom:** `FileNotFoundError: [Errno 2] No such file or directory: '/dev/ttyS0'`

**Cause:** The default serial port in `CommunicationManager` is `/dev/ttyS0`. Your device may be at a different path.

**Solution:** Pass the correct port via config:
```python
comm = CommunicationManager(config={"port": "/dev/ttyUSB0", "baud_rate": 9600})
```

On Windows, use `COM3` (or whichever port your device is on):
```python
comm = CommunicationManager(config={"port": "COM3"})
```

### Missing mission_config.json

**Symptom:** `FileNotFoundError: mission_config.json` when starting the flight controller

**Solution:** The controller looks for `mission_config.json` first in the CWD, then in the repository root. Either:
- Run from the repo root: `cd unisat && python flight-software/flight_controller.py`
- Pass an explicit path: `FlightController("/absolute/path/to/mission_config.json")`
- Generate one using the configurator: `cd configurator && streamlit run configurator_app.py`

### SQLite database locked

**Symptom:** `sqlite3.OperationalError: database is locked`

**Cause:** The DataLogger uses `check_same_thread=False` for async access. Multiple processes writing to the same database file simultaneously can cause locks.

**Solution:** Ensure only one FlightController instance writes to a given `db_dir` at a time. If testing, delete `data/telemetry_current.db` and restart.

---

## Ground Station Issues

### Streamlit: command not found

**Symptom:** `bash: streamlit: command not found`

**Solution:**
```bash
cd ground-station
pip install -r requirements.txt
# If still not found, use the module directly:
python -m streamlit run app.py
```

### Streamlit page not loading / blank screen

**Symptom:** The browser opens but the page is blank or shows a spinner indefinitely.

**Possible causes:**
1. **Missing dependencies:** Run `pip install -r ground-station/requirements.txt`
2. **Port conflict:** Streamlit defaults to port 8501. If it is in use:
   ```bash
   streamlit run app.py --server.port 8502
   ```
3. **Plotly version mismatch:** Ensure `plotly >= 5.18.0`.

### Ground station shows stale/demo data

**Symptom:** Dashboard displays synthetic data instead of real telemetry.

**Cause:** The ground station pages generate demo data when no serial connection is configured. This is by design for development.

**Solution:** To connect to real hardware, configure the serial port in `mission_config.json` under `ground_station.network_port` and ensure the TNC (e.g., Direwolf) is running and forwarding packets.

---

## Firmware Flash Issues

### ST-Link not detected

**Symptom:** `Error: unable to find a matching CMSIS-DAP device` or `No ST-Link detected`

**Solution:**
1. Check USB cable (use a data cable, not charge-only).
2. Install ST-Link drivers:
   - Linux: `sudo apt install stlink-tools`
   - Windows/macOS: Install [STM32CubeProgrammer](https://www.st.com/en/development-tools/stm32cubeprog.html)
3. Verify detection: `st-info --probe`

### Flash fails with "target voltage too low"

**Cause:** The Nucleo board is not powered, or the target MCU is in a locked state.

**Solution:**
1. Ensure the board is powered via USB or external supply.
2. If the MCU is locked, perform a full chip erase:
   ```bash
   st-flash erase
   ```
3. Then re-flash:
   ```bash
   st-flash write firmware/build/unisat_firmware.bin 0x08000000
   ```

### OpenOCD: flash write failed

**Solution using SWD with OpenOCD:**
```bash
openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
  -c "program firmware/build/unisat_firmware.elf verify reset exit"
```

If OpenOCD fails, try STM32CubeProgrammer as an alternative:
```bash
STM32_Programmer_CLI -c port=SWD -w firmware/build/unisat_firmware.bin 0x08000000 -v -rst
```

---

## Telemetry Decode Errors

### "Bad sync word" in TelemetryManager

**Symptom:** `Packet too short` or `Bad sync word: 0x...` errors in logs

**Cause:** The parser expects packets starting with the 4-byte sync word `0x1ACFFC1D`. Possible causes:
- Partial packet received (serial buffer underrun)
- Byte alignment lost due to noise on the link
- Non-CCSDS data on the serial port

**Solution:**
1. Increase the serial read timeout in `CommunicationManager`.
2. Check baud rate matches between firmware and ground station (default: 9600).
3. Verify the firmware is sending CCSDS-framed packets (check `CCSDS_Init()` was called).

### CRC mismatch in ground station parser

**Symptom:** `crc_valid: False` in parsed `CCSDSPacket`

**Cause:** The ground station `ccsds_parser.py` uses CRC-16/CCITT (poly 0x1021). The firmware must use the same polynomial.

**Solution:** Check `firmware/stm32/Core/Src/ccsds.c` uses the matching CRC algorithm. If you modified the firmware CRC, update `crc16_ccitt()` in `ground-station/utils/ccsds_parser.py` to match.

### Decoder returns empty dict

**Symptom:** `decode_obc(data)` or similar returns `{}`

**Cause:** The payload bytes are shorter than the decoder expects. Minimum sizes:
- OBC: 18 bytes
- EPS: 32 bytes
- ADCS: 34 bytes
- GNSS: 38 bytes
- Beacon: 14 bytes

**Solution:** Verify the firmware telemetry packing matches the expected struct layout. Check `firmware/stm32/Core/Src/telemetry.c` against the struct formats in `ground-station/utils/telemetry_decoder.py`.

---

## Simulation Issues

### Import errors in simulation scripts

**Symptom:** `ModuleNotFoundError: No module named 'orbit_simulator'`

**Cause:** The simulation scripts use relative imports and must be run from the `simulation/` directory.

**Solution:**
```bash
cd simulation
pip install -r requirements.txt
python mission_analyzer.py
```

### Plotly figures not displaying

**Symptom:** `plot_ground_track()` runs but no window appears.

**Solution:** The `visualize.py` script saves figures as HTML files. Open the generated files in a browser:
```bash
cd simulation
python visualize.py
# Open output_ground_track.html, output_power_budget.html, output_thermal.html
```

For interactive display, use Jupyter or call `fig.show()` instead of `fig.write_html()`.

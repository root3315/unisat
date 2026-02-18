# Assembly Guide

## Required Tools
- Soldering station (temperature-controlled)
- ESD wrist strap and mat
- Torque driver (M3 fasteners, 0.3 Nm)
- Multimeter
- Oscilloscope (for debug)

## Assembly Order

### Phase 1: Board Preparation
1. Populate OBC board (STM32F446RE, passives, connectors)
2. Populate EPS board (SPV1040, MOSFETs, inductors)
3. Populate COMM board (CC1125 + matching network)
4. Flash firmware via SWD: `./scripts/flash_stm32.sh`

### Phase 2: Battery Pack
1. Spot-weld 4× NCR18650B cells in 4S1P configuration
2. Add BMS protection board
3. Attach thermistor to center cell
4. Test: voltage should read 14.4-16.8V

### Phase 3: Solar Panel Integration
1. Solder solar cells to PCB (handle with care — fragile)
2. Connect panels to EPS board via JST connectors
3. Test MPPT under lamp: should show charging current

### Phase 4: Sensor Integration
1. Mount LIS3MDL, BME280, TMP117 on sensor board
2. Connect I2C bus (SDA/SCL with 4.7k pull-ups)
3. Mount MPU9250, connect SPI bus
4. Mount sun sensor photodiodes on each face
5. Run sensor self-test: `Sensors_SelfTest()`

### Phase 5: ADCS Assembly
1. Wind magnetorquer coils (200 turns each, 0.2mm wire)
2. Mount reaction wheels with brushless motors
3. Calibrate magnetometer (rotate 360° on each axis)

### Phase 6: Final Assembly
1. Stack all PCBs with M3 spacers (8mm gap)
2. Mount in CubeSat frame
3. Deploy antennas (verify mechanism)
4. Final electrical test (all buses, all sensors)
5. Vibration test (if available)

## Post-Assembly Checklist
- [ ] All sensors responding
- [ ] Battery charging from solar
- [ ] UHF beacon transmitting
- [ ] GNSS acquiring fix
- [ ] Camera capturing images
- [ ] Safe mode triggers correctly

# OBC Board — KiCad Project

STM32F446RE-based On-Board Computer PCB.

## Key Components
- STM32F446RE MCU (LQFP64)
- 8 MHz crystal oscillator
- 32.768 kHz RTC crystal
- MicroSD card slot (SPI)
- I2C bus connector (sensors)
- SPI bus connector (MPU9250, MCP3008)
- UART connectors (UHF, S-band)
- JTAG/SWD debug header
- Power input (5V regulated)

## PCB Specifications
- 4-layer PCB, 90x90mm
- Impedance-controlled traces for SPI
- Ground plane on layer 2

cmake_minimum_required(VERSION 3.20)

project(unisat_firmware
    VERSION 1.0.0
    DESCRIPTION "UniSat CubeSat Firmware"
    LANGUAGES C
)

# Cross-compilation settings for STM32F4
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# Toolchain
find_program(ARM_CC arm-none-eabi-gcc)
if(ARM_CC)
    set(CMAKE_C_COMPILER arm-none-eabi-gcc)
    set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)
    set(CMAKE_OBJCOPY arm-none-eabi-objcopy)
    set(CMAKE_SIZE arm-none-eabi-size)
    set(CROSS_COMPILE ON)
else()
    message(WARNING "ARM toolchain not found, building for host (test mode)")
    set(CROSS_COMPILE OFF)
endif()

# Compiler flags
set(MCU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")
set(OPT_FLAGS "-O2 -g")

if(CROSS_COMPILE)
    set(CMAKE_C_FLAGS "${MCU_FLAGS} ${OPT_FLAGS} -Wall -Wextra -Wpedantic -std=c11")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fdata-sections -ffunction-sections")
    set(CMAKE_EXE_LINKER_FLAGS "-Wl,--gc-sections -specs=nosys.specs -specs=nano.specs")
else()
    set(CMAKE_C_FLAGS "-Wall -Wextra -Wpedantic -std=c11 -g -DSIMULATION_MODE")
endif()

# Include directories
include_directories(
    stm32/Core/Inc
    stm32/Drivers/LIS3MDL
    stm32/Drivers/BME280
    stm32/Drivers/TMP117
    stm32/Drivers/MPU9250
    stm32/Drivers/SBM20
    stm32/Drivers/UBLOX
    stm32/Drivers/MCP3008
    stm32/Drivers/SunSensor
    stm32/ADCS
    stm32/EPS
)

# Source files
file(GLOB CORE_SOURCES "stm32/Core/Src/*.c")
file(GLOB DRIVER_SOURCES "stm32/Drivers/*/*.c")
file(GLOB ADCS_SOURCES "stm32/ADCS/*.c")
file(GLOB EPS_SOURCES "stm32/EPS/*.c")

set(ALL_SOURCES
    ${CORE_SOURCES}
    ${DRIVER_SOURCES}
    ${ADCS_SOURCES}
    ${EPS_SOURCES}
)

if(CROSS_COMPILE)
    add_executable(unisat_firmware.elf ${ALL_SOURCES})

    # Generate binary and hex files
    add_custom_command(TARGET unisat_firmware.elf POST_BUILD
        COMMAND ${CMAKE_OBJCOPY} -O binary $<TARGET_FILE:unisat_firmware.elf> unisat_firmware.bin
        COMMAND ${CMAKE_OBJCOPY} -O ihex $<TARGET_FILE:unisat_firmware.elf> unisat_firmware.hex
        COMMAND ${CMAKE_SIZE} $<TARGET_FILE:unisat_firmware.elf>
        COMMENT "Generating binary and hex files"
    )
else()
    # Host build for testing.
    # unisat_core is EXCLUDE_FROM_ALL — the full firmware source tree has
    # pre-existing host build errors in gnss.c (UBLOX_ReadByte signature
    # mismatch). Tests link only what they need via focused targets below.
    add_library(unisat_core STATIC EXCLUDE_FROM_ALL ${ALL_SOURCES})
    target_compile_definitions(unisat_core PUBLIC SIMULATION_MODE)

    # Test targets (host-only)
    enable_testing()

    add_executable(test_beacon_layout
        tests/test_beacon_layout.c
        tests/test_stubs.c
        stm32/Core/Src/telemetry.c
        stm32/Core/Src/ccsds.c
    )
    target_include_directories(test_beacon_layout PRIVATE
        tests
        stm32/Core/Inc
    )
    target_compile_definitions(test_beacon_layout PRIVATE SIMULATION_MODE)
    target_link_libraries(test_beacon_layout PRIVATE m)

    add_test(NAME beacon_layout COMMAND test_beacon_layout)

    # AX.25 library tests — pure, zero HAL/RTOS deps.
    add_executable(test_ax25_fcs
        tests/test_ax25_fcs.c
        stm32/Drivers/AX25/ax25.c
    )
    target_include_directories(test_ax25_fcs PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/AX25
    )
    target_compile_definitions(test_ax25_fcs PRIVATE SIMULATION_MODE)

    add_test(NAME ax25_fcs COMMAND test_ax25_fcs)

    add_executable(test_ax25_bitstuff
        tests/test_ax25_bitstuff.c
        stm32/Drivers/AX25/ax25.c
    )
    target_include_directories(test_ax25_bitstuff PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/AX25
    )
    target_compile_definitions(test_ax25_bitstuff PRIVATE SIMULATION_MODE)

    add_test(NAME ax25_bitstuff COMMAND test_ax25_bitstuff)

    add_executable(test_ax25_address
        tests/test_ax25_address.c
        stm32/Drivers/AX25/ax25.c
    )
    target_include_directories(test_ax25_address PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/AX25
    )
    target_compile_definitions(test_ax25_address PRIVATE SIMULATION_MODE)

    add_test(NAME ax25_address COMMAND test_ax25_address)
endif()

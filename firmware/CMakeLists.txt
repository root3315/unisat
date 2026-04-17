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
    stm32/Drivers/AX25
    stm32/Drivers/VirtualUART
    stm32/Drivers/Crypto
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
    # Host build for testing. unisat_core aggregates every firmware
    # source file so the host build doubles as a full-source compile
    # check — if a subsystem .c introduces a regression it fails here
    # even before any test target touches it.
    add_library(unisat_core STATIC ${ALL_SOURCES})
    target_compile_definitions(unisat_core PUBLIC SIMULATION_MODE)
    target_link_libraries(unisat_core PUBLIC m)

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

    add_executable(test_ax25_frame
        tests/test_ax25_frame.c
        stm32/Drivers/AX25/ax25.c
    )
    target_include_directories(test_ax25_frame PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/AX25
    )
    target_compile_definitions(test_ax25_frame PRIVATE SIMULATION_MODE)

    add_test(NAME ax25_frame COMMAND test_ax25_frame)

    # Cross-impl golden-vector verification (REQ-AX25-015).
    add_executable(test_ax25_golden
        tests/test_ax25_golden.c
        stm32/Drivers/AX25/ax25.c
    )
    target_include_directories(test_ax25_golden PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/AX25
        ${CMAKE_SOURCE_DIR}/../tests/golden
    )
    target_compile_definitions(test_ax25_golden PRIVATE SIMULATION_MODE)

    add_test(NAME ax25_golden COMMAND test_ax25_golden)

    # Streaming decoder (REQ-AX25-017/021/023/024).
    add_executable(test_ax25_decoder
        tests/test_ax25_decoder.c
        stm32/Drivers/AX25/ax25.c
        stm32/Drivers/AX25/ax25_decoder.c
    )
    target_include_directories(test_ax25_decoder PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/AX25
    )
    target_compile_definitions(test_ax25_decoder PRIVATE SIMULATION_MODE)

    add_test(NAME ax25_decoder COMMAND test_ax25_decoder)

    # Project-style facade (ADR-002).
    add_executable(test_ax25_api
        tests/test_ax25_api.c
        stm32/Drivers/AX25/ax25.c
        stm32/Drivers/AX25/ax25_decoder.c
    )
    target_include_directories(test_ax25_api PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/AX25
    )
    target_compile_definitions(test_ax25_api PRIVATE SIMULATION_MODE)

    add_test(NAME ax25_api COMMAND test_ax25_api)

    # comm.c integration — RX ring -> streaming decoder -> dispatcher.
    add_executable(test_comm_integration
        tests/test_comm_integration.c
        tests/test_stubs.c
        stm32/Core/Src/comm.c
        stm32/Core/Src/telemetry.c
        stm32/Core/Src/ccsds.c
        stm32/Drivers/AX25/ax25.c
        stm32/Drivers/AX25/ax25_decoder.c
    )
    target_include_directories(test_comm_integration PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/AX25
    )
    target_compile_definitions(test_comm_integration PRIVATE SIMULATION_MODE)
    target_link_libraries(test_comm_integration PRIVATE m)

    add_test(NAME comm_integration COMMAND test_comm_integration)

    # SITL virtual UART — cross-platform TCP loopback shim.
    add_executable(test_virtual_uart_build
        tests/test_virtual_uart_build.c
        stm32/Drivers/VirtualUART/virtual_uart.c
    )
    target_include_directories(test_virtual_uart_build PRIVATE
        tests
        stm32/Drivers/VirtualUART
    )
    target_compile_definitions(test_virtual_uart_build PRIVATE SIMULATION_MODE)
    if(WIN32)
        target_link_libraries(test_virtual_uart_build PRIVATE ws2_32)
    endif()

    add_test(NAME virtual_uart_build COMMAND test_virtual_uart_build)

    # ───────── Pre-existing subsystem tests (wired into CMake) ─────────

    add_executable(test_ccsds
        tests/test_ccsds.c
        stm32/Core/Src/ccsds.c
    )
    target_compile_definitions(test_ccsds PRIVATE SIMULATION_MODE)
    add_test(NAME ccsds COMMAND test_ccsds)

    add_executable(test_adcs_algorithms
        tests/test_adcs_algorithms.c
        stm32/ADCS/quaternion.c
        stm32/ADCS/bdot.c
    )
    target_compile_definitions(test_adcs_algorithms PRIVATE SIMULATION_MODE)
    target_link_libraries(test_adcs_algorithms PRIVATE m)
    add_test(NAME adcs_algorithms COMMAND test_adcs_algorithms)

    add_executable(test_eps
        tests/test_eps.c
        stm32/EPS/mppt.c
        stm32/EPS/battery_manager.c
    )
    target_compile_definitions(test_eps PRIVATE SIMULATION_MODE)
    target_link_libraries(test_eps PRIVATE m)
    add_test(NAME eps COMMAND test_eps)

    add_executable(test_telemetry
        tests/test_telemetry.c
    )
    target_compile_definitions(test_telemetry PRIVATE SIMULATION_MODE)
    add_test(NAME telemetry_placeholder COMMAND test_telemetry)

    add_executable(test_hmac
        tests/test_hmac.c
        stm32/Drivers/Crypto/sha256.c
        stm32/Drivers/Crypto/hmac_sha256.c
    )
    target_compile_definitions(test_hmac PRIVATE SIMULATION_MODE)
    add_test(NAME hmac COMMAND test_hmac)

    # ───────── SITL firmware demo binary ─────────

    add_executable(sitl_fw
        ${CMAKE_SOURCE_DIR}/../scripts/sitl_fw.c
        stm32/Drivers/VirtualUART/virtual_uart.c
        stm32/Drivers/AX25/ax25.c
        stm32/Drivers/AX25/ax25_decoder.c
    )
    target_include_directories(sitl_fw PRIVATE
        stm32/Core/Inc
        stm32/Drivers/AX25
        stm32/Drivers/VirtualUART
    )
    target_compile_definitions(sitl_fw PRIVATE SIMULATION_MODE)
    if(WIN32)
        target_link_libraries(sitl_fw PRIVATE ws2_32)
    endif()
endif()

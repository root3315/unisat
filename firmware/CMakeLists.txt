cmake_minimum_required(VERSION 3.20)

#
# Toolchain detection MUST run before project() so CMake's compiler
# probes the right compiler. When arm-none-eabi-gcc is on PATH we
# produce a real STM32F446RE firmware image; otherwise we fall back
# to a host static library used by the ctest + pytest pipelines.
#
find_program(ARM_CC arm-none-eabi-gcc)
if(ARM_CC)
    set(CMAKE_SYSTEM_NAME      Generic)
    set(CMAKE_SYSTEM_PROCESSOR arm)
    set(CMAKE_C_COMPILER       arm-none-eabi-gcc)
    set(CMAKE_ASM_COMPILER     arm-none-eabi-gcc)
    set(CMAKE_OBJCOPY          arm-none-eabi-objcopy)
    set(CMAKE_SIZE             arm-none-eabi-size)
    # Skip GCC link probe — no crt0 for bare-metal, only .elf output.
    set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
    set(CROSS_COMPILE ON)
else()
    message(STATUS "arm-none-eabi-gcc not found — host build (SIMULATION_MODE)")
    set(CROSS_COMPILE OFF)
endif()

project(unisat_firmware
    VERSION 1.1.0
    DESCRIPTION "UniSat CubeSat Firmware"
    LANGUAGES C ASM
)

#
# Compiler flags.
# Shared: -Wall -Wextra -Wpedantic -std=c11 across both paths so the
# host build catches any regression the ARM build would also reject.
# Phase 5 will add -Werror behind an opt-in STRICT=ON gate.
#
set(MCU_FLAGS "-mcpu=cortex-m4 -mthumb -mfpu=fpv4-sp-d16 -mfloat-abi=hard")
set(OPT_FLAGS "-Og -g3")

#
# Phase 5 opt-in build-quality gates.
#   -DSTRICT=ON       : host build promotes warnings to errors
#                        (-Werror) and enables -Wshadow -Wconversion
#                        so every regression surfaces immediately.
#   -DCOVERAGE=ON     : host build emits gcov counters; the `coverage`
#                        target runs lcov + genhtml for a report.
#   -DSANITIZERS=ON   : host build links AddressSanitizer +
#                        UndefinedBehaviorSanitizer. Catches
#                        out-of-bounds, use-after-free, shift of
#                        negative value, etc. Host-only — the target
#                        toolchain has no runtime for these.
#
option(STRICT     "Host build: -Werror + extra warnings"    OFF)
option(COVERAGE   "Host build: gcov coverage instrumentation" OFF)
option(SANITIZERS "Host build: ASAN + UBSAN"                OFF)

if(CROSS_COMPILE)
    set(CMAKE_C_FLAGS
        "${MCU_FLAGS} ${OPT_FLAGS} -Wall -Wextra -Wpedantic -std=c11 \
        -fdata-sections -ffunction-sections -fstack-usage \
        -DSTM32F446xx")
    set(CMAKE_ASM_FLAGS "${MCU_FLAGS} -x assembler-with-cpp")

    # Linker script path is anchored to the Target/ directory next to
    # the startup.s that knows about these symbols. -Map emits a full
    # static memory map for the Phase 5 size-budget CI check.
    set(LINKER_SCRIPT
        "${CMAKE_CURRENT_SOURCE_DIR}/stm32/Target/STM32F446RETx_FLASH.ld")

    set(CMAKE_EXE_LINKER_FLAGS
        "${MCU_FLAGS} -T${LINKER_SCRIPT} \
        -specs=nosys.specs -specs=nano.specs \
        -Wl,--gc-sections,--print-memory-usage \
        -Wl,-Map=unisat_firmware.map,--cref")
else()
    set(CMAKE_C_FLAGS "-Wall -Wextra -Wpedantic -std=c11 -g -DSIMULATION_MODE")

    if(STRICT)
        # -Werror gates the CI; -Wshadow catches the classic local
        # variable shadowing a module-scope name bug; -Wconversion
        # surfaces narrowing casts that matter on the 32-bit MCU.
        # Keep off by default so a regular `make test` during
        # development isn't blocked by a benign third-party warning.
        #
        # unused-function is demoted because several sensor drivers
        # gate their real helpers behind #ifndef SIMULATION_MODE —
        # the helpers are defined but never referenced in the host
        # build, which is expected and uninteresting.
        set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Werror -Wshadow -Wconversion \
            -Wno-error=unused-variable -Wno-error=unused-parameter \
            -Wno-error=unused-but-set-variable \
            -Wno-error=unused-function \
            -Wno-error=unused-const-variable")
    endif()
    if(COVERAGE)
        # --coverage is short for -fprofile-arcs -ftest-coverage on
        # compile and -lgcov on link.
        set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} --coverage -O0")
        set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} --coverage")
    endif()
    if(SANITIZERS)
        set(SAN_FLAGS "-fsanitize=address,undefined -fno-omit-frame-pointer")
        set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${SAN_FLAGS}")
        set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${SAN_FLAGS}")
    endif()
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
    stm32/Drivers/BoardTemp
    stm32/ADCS
    stm32/EPS
)

# Source files — application + drivers + subsystems (shared by host and ARM).
file(GLOB CORE_SOURCES   "stm32/Core/Src/*.c")
file(GLOB DRIVER_SOURCES "stm32/Drivers/*/*.c")
file(GLOB ADCS_SOURCES   "stm32/ADCS/*.c")
file(GLOB EPS_SOURCES    "stm32/EPS/*.c")

# Target-only sources: LD-anchored vectors, CMSIS SystemInit, clock
# config, exception handlers, and weak HAL fallback. Globbed separately
# so the host build never pulls them in (would produce bare-register
# writes into x86 address space).
file(GLOB TARGET_C_SOURCES "stm32/Target/*.c")
set(TARGET_ASM_SOURCES
    "${CMAKE_CURRENT_SOURCE_DIR}/stm32/Target/startup_stm32f446retx.s"
)

set(ALL_SOURCES
    ${CORE_SOURCES}
    ${DRIVER_SOURCES}
    ${ADCS_SOURCES}
    ${EPS_SOURCES}
)

#
# HAL auto-detect — if scripts/setup_stm32_hal.sh has been run, link
# the full STM32Cube HAL and drop our weak hal_shim.c (its strong
# counterparts in HAL_Driver/Src override every symbol we stubbed).
# If the user has not fetched HAL, the build still succeeds and the
# shim keeps the linker happy — firmware boots, clocks up, executes,
# but every sensor/bus call returns HAL_ERROR until HAL is installed.
#
set(HAL_DRIVER_DIR "${CMAKE_CURRENT_SOURCE_DIR}/stm32/Drivers/STM32F4xx_HAL_Driver")
set(CMSIS_DEVICE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/stm32/Drivers/CMSIS/Include")
if(CROSS_COMPILE AND EXISTS "${HAL_DRIVER_DIR}/Src" AND EXISTS "${CMSIS_DEVICE_DIR}")
    message(STATUS "STM32Cube HAL detected — linking full driver set")
    file(GLOB HAL_SOURCES "${HAL_DRIVER_DIR}/Src/*.c")
    list(REMOVE_ITEM HAL_SOURCES
        "${HAL_DRIVER_DIR}/Src/stm32f4xx_hal_timebase_rtc_alarm_template.c"
        "${HAL_DRIVER_DIR}/Src/stm32f4xx_hal_timebase_rtc_wakeup_template.c"
        "${HAL_DRIVER_DIR}/Src/stm32f4xx_hal_timebase_tim_template.c"
    )
    list(APPEND TARGET_C_SOURCES ${HAL_SOURCES})
    list(REMOVE_ITEM TARGET_C_SOURCES "${CMAKE_CURRENT_SOURCE_DIR}/stm32/Target/hal_shim.c")
    include_directories("${HAL_DRIVER_DIR}/Inc" "${CMSIS_DEVICE_DIR}"
                        "${CMAKE_CURRENT_SOURCE_DIR}/stm32/Drivers/CMSIS/CMSIS_Include")
    set(HAS_FULL_HAL ON)
else()
    if(CROSS_COMPILE)
        message(STATUS "STM32Cube HAL not found — hal_shim.c will be linked")
        message(STATUS "    run scripts/setup_stm32_hal.sh for a production build")
    endif()
    set(HAS_FULL_HAL OFF)
endif()

if(CROSS_COMPILE)
    add_executable(unisat_firmware.elf
        ${ALL_SOURCES}
        ${TARGET_C_SOURCES}
        ${TARGET_ASM_SOURCES}
    )
    set_target_properties(unisat_firmware.elf PROPERTIES
        LINK_DEPENDS "${LINKER_SCRIPT}"
    )

    # Post-build: .bin + .hex + size report. The --format=berkeley output
    # is what st-flash consumes; the separate .hex is convenient for
    # STM32CubeProgrammer / OpenOCD workflows that parse Intel-hex.
    add_custom_command(TARGET unisat_firmware.elf POST_BUILD
        COMMAND ${CMAKE_OBJCOPY} -O binary
                $<TARGET_FILE:unisat_firmware.elf> unisat_firmware.bin
        COMMAND ${CMAKE_OBJCOPY} -O ihex
                $<TARGET_FILE:unisat_firmware.elf> unisat_firmware.hex
        COMMAND ${CMAKE_SIZE} --format=berkeley
                $<TARGET_FILE:unisat_firmware.elf>
        COMMENT "Generating .bin/.hex and printing section sizes"
    )

    # Convenience targets so `cmake --build build --target flash` works
    # anywhere arm-none-eabi-gcc + st-flash are installed. Size is a
    # cheap gate for catching flash/RAM overflow early — Phase 5 wires
    # it into the CI budget check.
    add_custom_target(flash
        COMMAND st-flash write unisat_firmware.bin 0x08000000
        COMMAND st-flash reset
        DEPENDS unisat_firmware.elf
        COMMENT "Flashing firmware to STM32F446RE via ST-Link"
    )

    add_custom_target(size
        COMMAND ${CMAKE_SIZE} --format=sysv
                $<TARGET_FILE:unisat_firmware.elf>
        DEPENDS unisat_firmware.elf
        COMMENT "Per-section flash / RAM usage"
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
        stm32/Drivers/BoardTemp/board_temp.c
        stm32/Drivers/TMP117/tmp117.c
        stm32/Core/Src/fdir.c
    )
    target_include_directories(test_beacon_layout PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/BoardTemp
        stm32/Drivers/TMP117
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
        stm32/Core/Src/fdir.c
        stm32/Drivers/AX25/ax25.c
        stm32/Drivers/AX25/ax25_decoder.c
        stm32/Drivers/BoardTemp/board_temp.c
        stm32/Drivers/TMP117/tmp117.c
    )
    target_include_directories(test_comm_integration PRIVATE
        tests
        stm32/Core/Inc
        stm32/Drivers/AX25
        stm32/Drivers/BoardTemp
        stm32/Drivers/TMP117
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

    # Track 1b — HMAC-authenticated command dispatcher.
    add_executable(test_command_dispatcher
        tests/test_command_dispatcher.c
        stm32/Core/Src/command_dispatcher.c
        stm32/Drivers/Crypto/sha256.c
        stm32/Drivers/Crypto/hmac_sha256.c
    )
    target_compile_definitions(test_command_dispatcher PRIVATE SIMULATION_MODE)
    add_test(NAME command_dispatcher COMMAND test_command_dispatcher)

    # Phase 2 / M1a — persistent HMAC key store with rotation.
    # Test file supplies its own strong platform_read/write/erase
    # hooks (fault-injection for corrupt-slot and backend-fail cases),
    # which override the weak defaults in key_store.c.
    add_executable(test_key_store
        tests/test_key_store.c
        stm32/Core/Src/key_store.c
    )
    target_compile_definitions(test_key_store PRIVATE SIMULATION_MODE)
    add_test(NAME key_store COMMAND test_key_store)

    # Boot-time security integration — key_store -> dispatcher wiring.
    # Links the real key_store.c and command_dispatcher.c together
    # (no stubs) so the end-to-end fail-closed + warm-reboot-rotation
    # paths main.c relies on are proven in CI.
    add_executable(test_boot_security
        tests/test_boot_security.c
        stm32/Core/Src/key_store.c
        stm32/Core/Src/command_dispatcher.c
        stm32/Drivers/Crypto/sha256.c
        stm32/Drivers/Crypto/hmac_sha256.c
    )
    target_compile_definitions(test_boot_security PRIVATE SIMULATION_MODE)
    add_test(NAME boot_security COMMAND test_boot_security)

    # Phase 3 — Fault Detection, Isolation, Recovery (FDIR).
    # Test supplies its own strong FDIR_GetTick so escalation timing
    # is deterministic without HAL_GetTick.
    add_executable(test_fdir
        tests/test_fdir.c
        stm32/Core/Src/fdir.c
    )
    target_compile_definitions(test_fdir PRIVATE SIMULATION_MODE)
    add_test(NAME fdir COMMAND test_fdir)

    # Phase 3 follow-up — FDIR-driven mode supervisor.
    add_executable(test_mode_manager
        tests/test_mode_manager.c
        stm32/Core/Src/mode_manager.c
        stm32/Core/Src/fdir.c
    )
    target_compile_definitions(test_mode_manager PRIVATE SIMULATION_MODE)
    add_test(NAME mode_manager COMMAND test_mode_manager)

    # Phase 7 #4 — warm-reboot-survivable fault log (.noinit on target,
    # plain .bss on host). Test links the real implementation and
    # overrides FDIR_GetTick for deterministic timestamps.
    add_executable(test_fdir_persistent
        tests/test_fdir_persistent.c
        stm32/Core/Src/fdir_persistent.c
    )
    target_compile_definitions(test_fdir_persistent PRIVATE SIMULATION_MODE)
    add_test(NAME fdir_persistent COMMAND test_fdir_persistent)

    # Phase 4 — Board-temperature facade (Tboard beacon field).
    # Deliberately DOES NOT link tmp117.c; the test provides its own
    # strong TMP117_Init / TMP117_Read so bus-failure and
    # out-of-range scenarios are exercised deterministically.
    add_executable(test_board_temp
        tests/test_board_temp.c
        stm32/Drivers/BoardTemp/board_temp.c
        stm32/Core/Src/fdir.c
    )
    target_compile_definitions(test_board_temp PRIVATE SIMULATION_MODE)
    target_link_libraries(test_board_temp PRIVATE m)
    add_test(NAME board_temp COMMAND test_board_temp)

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

    # ───────── Phase 5: coverage target ─────────
    #
    # Runs ctest, then lcov + genhtml to produce an HTML report under
    # build/coverage_html/ and a flat line-coverage percentage the CI
    # scripts can parse. Requires the host build to have been
    # configured with -DCOVERAGE=ON so gcov counters are embedded.
    #
    # Usage (from repo root):
    #   cmake -B firmware/build -S firmware -DCOVERAGE=ON
    #   cmake --build firmware/build
    #   cmake --build firmware/build --target coverage
    #
    if(COVERAGE)
        find_program(LCOV_BIN    lcov)
        find_program(GENHTML_BIN genhtml)
        if(LCOV_BIN AND GENHTML_BIN)
            add_custom_target(coverage
                COMMAND ${LCOV_BIN} --zerocounters --directory .
                COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
                COMMAND ${LCOV_BIN} --capture --directory .
                        --output-file coverage.info
                        --rc geninfo_unexecuted_blocks=1
                        --ignore-errors mismatch,negative
                COMMAND ${LCOV_BIN} --remove coverage.info
                        "*/tests/*" "*/unity/*" "/usr/*"
                        --output-file coverage.info
                        --ignore-errors unused
                COMMAND ${LCOV_BIN} --list coverage.info
                COMMAND ${GENHTML_BIN} coverage.info
                        --output-directory coverage_html --quiet
                COMMENT "gcov + lcov + genhtml -> coverage_html/"
                WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            )
        else()
            message(WARNING "COVERAGE=ON but lcov / genhtml missing — "
                            "install lcov package to enable the report target")
        endif()
    endif()
endif()

/**
 * @file board_temp.h
 * @brief Board-temperature facade (beacon byte 14-15 Tboard source).
 *
 * Rationale
 * ---------
 * The UniSat OBC already carries a TMP117 precision sensor on the
 * main PCB (see Drivers/TMP117/). Before Phase 4 the beacon packer
 * wrote zero into the 16-bit Tboard field because telemetry.c had
 * no direct handle on any sensor — telemetry only consumed the
 * aggregate status structs (OBC_Status_t, EPS_Status_t, ...), and
 * the existing sensors.c routed TMP117 readings into
 * SensorData_t.temp_precise which was not exposed to the beacon
 * packer. Rather than threading raw SensorData_t through the
 * telemetry API (which already has a settled contract), this
 * module publishes the most recent board-temperature reading via
 * a thin facade the telemetry packer can call without pulling
 * the full sensors module.
 *
 * Contract
 * --------
 *   BoardTemp_Init()      — called once at boot after MX_I2C1_Init
 *                           has set up the sensor bus. Configures
 *                           the underlying TMP117 and puts the
 *                           reading cache into a known state.
 *   BoardTemp_Update()    — pulls a fresh reading into the cache.
 *                           Meant to be called from SensorTask at
 *                           the sensor-poll cadence (1 Hz).
 *   BoardTemp_GetC()      — returns the most recent reading, in °C.
 *                           Before the first successful Update,
 *                           returns 0.0f and sets *is_valid to false.
 *
 * The facade is deliberately bus-agnostic at the API level — a
 * future hardware revision that substitutes TMP117 for something
 * else only has to supply a different board_temp.c.
 */
#ifndef BOARD_TEMP_H
#define BOARD_TEMP_H

#include <stdint.h>
#include <stdbool.h>

/** Initialise the underlying temperature sensor. Returns true on
 *  success, false if the bus / device is not responding. Safe to
 *  call repeatedly (re-init on a bus-reset recovery path). */
bool BoardTemp_Init(void);

/** Pull a fresh reading into the module cache. Returns true on a
 *  valid measurement; on bus/device error the cache is NOT
 *  invalidated — consumers keep the last good value and an FDIR
 *  fault is reported for the bus. */
bool BoardTemp_Update(void);

/** Return the most-recent board-temperature reading.
 *  @param is_valid  optional pointer — set to true if at least one
 *                   successful Update has landed, false otherwise.
 *  @return temperature in °C. Zero when is_valid is false. */
float BoardTemp_GetC(bool *is_valid);

/** Convert the cached temperature to the beacon wire format
 *  (signed 16-bit, 0.1 °C units, saturating at ±327.6 °C).
 *  Central helper so the telemetry packer doesn't duplicate the
 *  scaling arithmetic. */
int16_t BoardTemp_GetScaled0p1(void);

#endif /* BOARD_TEMP_H */

/**
 * @file board_temp.c
 * @brief Board-temperature facade over the TMP117 sensor.
 *
 * Light wrapper with two goals:
 *   1. Cache the most-recent valid reading so the beacon packer
 *      can pull the value without touching TMP117_Read() from a
 *      time-sensitive CCSDS packer path.
 *   2. Route any bus / device error into FDIR so the I2C bus-stuck
 *      escalation policy (see docs/reliability/fdir.md) applies —
 *      a sticky TMP117 no-ACK is the same class of event as any
 *      other I2C sensor failure and is handled uniformly.
 *
 * The module is headless on host builds: TMP117_Init / TMP117_Read
 * are provided by the existing TMP117 driver which in SIMULATION_MODE
 * returns benign constants, so BoardTemp_GetC() reports 25 °C on
 * host without any HW backing.
 */

#include "board_temp.h"
#include "tmp117.h"
#include "fdir.h"
#include <math.h>

/* Cached state. is_valid turns true only after the first successful
 * Update — a failed Init + zero-read-on-first-Update would otherwise
 * advertise a plausible-looking 0.0 °C reading which is worse than
 * an obviously-wrong sentinel. */
static TMP117_Handle_t s_dev;
static float s_last_c = 0.0f;
static bool  s_valid = false;

bool BoardTemp_Init(void)
{
    /* A fresh Init drops any previously-cached reading — a caller
     * invoking Init twice after e.g. an I2C bus-reset should not
     * see stale data advertised as "valid". */
    s_last_c = 0.0f;
    s_valid  = false;

    /* Default I2C address on the UniSat OBC (ADD0 tied to GND). The
     * TMP117 driver stores the 7-bit address in the .addr field; the
     * i2c_handle is filled by the caller / platform layer on target. */
    s_dev.addr = TMP117_DEFAULT_ADDR;
    s_dev.i2c_handle = NULL;

    TMP117_Status_t st = TMP117_Init(&s_dev);
    if (st != TMP117_OK) {
        /* Any non-zero status is a sensor / bus anomaly — tell FDIR
         * so the first-boot failure contributes to the escalation
         * window on the real bus. On host (SIMULATION_MODE) TMP117
         * returns 0 so this branch is not taken. */
        FDIR_Report(FAULT_SENSOR_OUT_OF_RANGE);
        return false;
    }

    /* Don't mark valid until the first real Update — Init only
     * confirms the device is on the bus. */
    return true;
}

bool BoardTemp_Update(void)
{
    float t = 0.0f;
    TMP117_Status_t st = TMP117_Read(&s_dev, &t);
    if (st != TMP117_OK) {
        FDIR_Report(FAULT_I2C_BUS_STUCK);
        /* Preserve the last good value so a transient bus glitch
         * doesn't cause a visible step in beacon telemetry. */
        return false;
    }

    /* Reasonable clamp. TMP117 datasheet range is -55..+125 °C;
     * anything outside that is a wiring / EMI event rather than a
     * physical reading. */
    if (!isfinite(t) || t < -60.0f || t > 130.0f) {
        FDIR_Report(FAULT_SENSOR_OUT_OF_RANGE);
        return false;
    }

    s_last_c = t;
    s_valid  = true;
    return true;
}

float BoardTemp_GetC(bool *is_valid)
{
    if (is_valid != NULL) { *is_valid = s_valid; }
    return s_valid ? s_last_c : 0.0f;
}

int16_t BoardTemp_GetScaled0p1(void)
{
    if (!s_valid) { return 0; }

    /* 0.1 °C units, saturated to i16 range. i16 max = 32767 =>
     * 3276.7 °C, so saturation only matters for the lower bound
     * of a cold-soak event; still guard both sides defensively. */
    float scaled = s_last_c * 10.0f;
    if (scaled >  32767.0f) { return  32767; }
    if (scaled < -32768.0f) { return -32768; }

    /* Explicit round-half-away-from-zero so a −20.05 °C reading
     * packs as −201, not −200 (nearest-even would be implementation-
     * defined on some toolchains for the .5 case). */
    float bias = (scaled >= 0.0f) ? 0.5f : -0.5f;
    return (int16_t)(scaled + bias);
}

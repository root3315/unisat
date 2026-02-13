/**
 * @file sbm20.h
 * @brief HAL driver for SBM-20 Geiger-Muller tube (GPIO pulse counting)
 *
 * The SBM-20 is a Soviet-era GM tube commonly used for radiation detection.
 * This driver counts pulses via a GPIO interrupt and derives counts per
 * second (CPS), counts per minute (CPM), and equivalent dose rate.
 *
 * @note Conversion factor: 1 CPM = 0.0057 uSv/h for SBM-20
 * @note Dead time: ~190 us (internal quenching)
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#ifndef SBM20_H
#define SBM20_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stdbool.h>

/* ───────────── SBM-20 Characteristics ───────────── */

/** Conversion factor: CPM to uSv/h for SBM-20 tube */
#define SBM20_CPM_TO_USVH      0.0057f

/** Dead time in microseconds (halogen self-quenching) */
#define SBM20_DEAD_TIME_US      190

/** Length of the sliding window for CPM calculation (seconds) */
#define SBM20_WINDOW_SIZE       60

/* ───────────── Return Codes ───────────── */

typedef enum {
    SBM20_OK = 0,                    /**< Operation succeeded */
    SBM20_ERR_NOT_INIT,              /**< Driver not initialized */
    SBM20_ERR_INVALID_PARAM,         /**< Invalid parameter */
    SBM20_ERR_SELF_TEST              /**< Self-test failed */
} SBM20_Status_t;

/* ───────────── Handle ───────────── */

/**
 * @brief Driver instance handle.
 *
 * Maintains a circular buffer of per-second pulse counts for accurate
 * CPM calculation with a 60-second sliding window.
 */
typedef struct {
    volatile uint32_t pulse_count;           /**< Raw pulse counter (ISR-incremented) */
    uint32_t          window[SBM20_WINDOW_SIZE]; /**< Per-second counts ring buffer */
    uint8_t           window_idx;            /**< Current position in ring buffer */
    uint8_t           window_filled;         /**< Number of valid entries in window */
    uint32_t          last_cps;              /**< Most recent CPS snapshot */
    uint32_t          total_counts;          /**< Lifetime total counts */
    bool              initialized;           /**< True after successful init */
} SBM20_Handle_t;

/* ───────────── Public API ───────────── */

/**
 * @brief Initialize the SBM-20 driver.
 *
 * Zeroes all counters and prepares the sliding window.  The caller must
 * separately configure the GPIO EXTI interrupt and call SBM20_IRQHandler()
 * from the ISR.
 *
 * @param[in,out] dev  Driver handle.
 * @return SBM20_OK on success.
 */
SBM20_Status_t SBM20_Init(SBM20_Handle_t *dev);

/**
 * @brief Interrupt handler — call from the GPIO EXTI ISR.
 *
 * Increments the raw pulse counter.  Must be called once per detected
 * falling edge on the GM tube output pin.
 *
 * @param[in,out] dev  Initialized driver handle.
 */
void SBM20_IRQHandler(SBM20_Handle_t *dev);

/**
 * @brief Periodic tick — call once per second from a timer ISR or task.
 *
 * Snapshots the current pulse count into the sliding window and resets
 * the per-second counter.
 *
 * @param[in,out] dev  Initialized driver handle.
 */
void SBM20_Tick1s(SBM20_Handle_t *dev);

/**
 * @brief Get the most recent counts per second.
 *
 * @param[in]  dev  Initialized driver handle.
 * @param[out] cps  Counts per second.
 * @return SBM20_OK on success.
 */
SBM20_Status_t SBM20_GetCPS(SBM20_Handle_t *dev, uint32_t *cps);

/**
 * @brief Get counts per minute (60-second sliding window).
 *
 * If fewer than 60 seconds have elapsed since init, the CPM is
 * extrapolated from available data.
 *
 * @param[in]  dev  Initialized driver handle.
 * @param[out] cpm  Counts per minute.
 * @return SBM20_OK on success.
 */
SBM20_Status_t SBM20_GetCPM(SBM20_Handle_t *dev, uint32_t *cpm);

/**
 * @brief Get equivalent dose rate in uSv/h.
 *
 * Uses the SBM-20 conversion factor (0.0057 uSv/h per CPM).
 *
 * @param[in]  dev       Initialized driver handle.
 * @param[out] dose_rate Dose rate in micro-Sieverts per hour.
 * @return SBM20_OK on success.
 */
SBM20_Status_t SBM20_GetDoseRate(SBM20_Handle_t *dev, float *dose_rate);

/**
 * @brief Execute a basic self-test.
 *
 * Checks that the driver is initialized and that the sliding window
 * mechanism is functional.
 *
 * @param[in] dev  Initialized driver handle.
 * @return SBM20_OK if self-test passes.
 */
SBM20_Status_t SBM20_SelfTest(SBM20_Handle_t *dev);

#ifdef __cplusplus
}
#endif

#endif /* SBM20_H */

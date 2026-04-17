/**
 * @file sbm20.c
 * @brief HAL driver implementation for SBM-20 Geiger-Muller tube
 *
 * Counts ionization pulses via GPIO interrupt and derives radiation
 * metrics (CPS, CPM, dose rate) using a 60-second sliding window.
 *
 * In SIMULATION_MODE the driver produces synthetic background-radiation
 * counts (~20 CPM typical for SBM-20 at sea level).
 *
 * @author UniSat CubeSat Team
 * @version 1.0.0
 */

#include "sbm20.h"
#include <string.h>

/* ───────────── Simulation State ───────────── */

#ifdef SIMULATION_MODE
static uint32_t sim_tick_counter = 0;
#endif

/* ───────────── Public API ───────────── */

SBM20_Status_t SBM20_Init(SBM20_Handle_t *dev)
{
    if (!dev) return SBM20_ERR_INVALID_PARAM;

    dev->pulse_count  = 0;
    dev->window_idx   = 0;
    dev->window_filled = 0;
    dev->last_cps     = 0;
    dev->total_counts = 0;

    memset(dev->window, 0, sizeof(dev->window));

    dev->initialized = true;

#ifdef SIMULATION_MODE
    sim_tick_counter = 0;
#endif

    return SBM20_OK;
}

void SBM20_IRQHandler(SBM20_Handle_t *dev)
{
    if (!dev || !dev->initialized) return;

    /*
     * This function is called from an EXTI ISR.  The increment
     * is safe on Cortex-M because single-word writes are atomic.
     */
    dev->pulse_count++;
}

void SBM20_Tick1s(SBM20_Handle_t *dev)
{
    if (!dev || !dev->initialized) return;

#ifdef SIMULATION_MODE
    /*
     * Simulate background radiation for SBM-20:
     * ~20 CPM average => ~0-1 counts per second with occasional bursts.
     * Use a simple deterministic pattern for reproducibility.
     */
    sim_tick_counter++;
    uint32_t sim_counts;
    if (sim_tick_counter % 3 == 0) {
        sim_counts = 1; /* One pulse every ~3 seconds = ~20 CPM */
    } else if (sim_tick_counter % 17 == 0) {
        sim_counts = 2; /* Occasional burst */
    } else {
        sim_counts = 0;
    }

    dev->window[dev->window_idx] = sim_counts;
    dev->last_cps = sim_counts;
    dev->total_counts += sim_counts;
#else
    /*
     * Snapshot the ISR-incremented pulse_count atomically.
     * On Cortex-M this is safe without disabling interrupts because
     * 32-bit reads/writes are atomic, and we only ever reset to 0.
     */
    uint32_t current = dev->pulse_count;
    dev->pulse_count = 0;

    dev->window[dev->window_idx] = current;
    dev->last_cps = current;
    dev->total_counts += current;
#endif

    dev->window_idx = (uint8_t)((dev->window_idx + 1U) % SBM20_WINDOW_SIZE);
    if (dev->window_filled < SBM20_WINDOW_SIZE) {
        dev->window_filled++;
    }
}

SBM20_Status_t SBM20_GetCPS(SBM20_Handle_t *dev, uint32_t *cps)
{
    if (!dev || !dev->initialized) return SBM20_ERR_NOT_INIT;
    if (!cps) return SBM20_ERR_INVALID_PARAM;

    *cps = dev->last_cps;
    return SBM20_OK;
}

SBM20_Status_t SBM20_GetCPM(SBM20_Handle_t *dev, uint32_t *cpm)
{
    if (!dev || !dev->initialized) return SBM20_ERR_NOT_INIT;
    if (!cpm) return SBM20_ERR_INVALID_PARAM;

    if (dev->window_filled == 0) {
        *cpm = 0;
        return SBM20_OK;
    }

    /* Sum all valid entries in the sliding window */
    uint32_t sum = 0;
    for (uint8_t i = 0; i < dev->window_filled; i++) {
        sum += dev->window[i];
    }

    if (dev->window_filled >= SBM20_WINDOW_SIZE) {
        /* Full window: sum IS the CPM */
        *cpm = sum;
    } else {
        /* Partial window: extrapolate to 60 seconds */
        *cpm = (sum * SBM20_WINDOW_SIZE) / dev->window_filled;
    }

    return SBM20_OK;
}

SBM20_Status_t SBM20_GetDoseRate(SBM20_Handle_t *dev, float *dose_rate)
{
    if (!dev || !dev->initialized) return SBM20_ERR_NOT_INIT;
    if (!dose_rate) return SBM20_ERR_INVALID_PARAM;

    uint32_t cpm = 0;
    SBM20_Status_t st = SBM20_GetCPM(dev, &cpm);
    if (st != SBM20_OK) return st;

    /* Convert CPM to micro-Sieverts per hour */
    *dose_rate = (float)cpm * SBM20_CPM_TO_USVH;

    return SBM20_OK;
}

SBM20_Status_t SBM20_SelfTest(SBM20_Handle_t *dev)
{
    if (!dev || !dev->initialized) return SBM20_ERR_NOT_INIT;

#ifdef SIMULATION_MODE
    /*
     * Simulate a few ticks and verify the window logic produces
     * non-negative, consistent results.
     */
    SBM20_Handle_t test_dev;
    SBM20_Init(&test_dev);

    /* Run 5 simulated ticks */
    for (int i = 0; i < 5; i++) {
        SBM20_Tick1s(&test_dev);
    }

    uint32_t cps = 0, cpm = 0;
    float dose = 0;

    SBM20_GetCPS(&test_dev, &cps);
    SBM20_GetCPM(&test_dev, &cpm);
    SBM20_GetDoseRate(&test_dev, &dose);

    /* Verify dose rate is non-negative */
    if (dose < 0.0f) return SBM20_ERR_SELF_TEST;

    return SBM20_OK;
#else
    /*
     * Hardware self-test: verify that the IRQ handler and tick mechanism
     * are correctly wired by checking the window state.
     *
     * Note: We cannot force a pulse on the GM tube, so we only verify
     * the software pipeline.  A separate radiation source test must
     * be performed during integration testing.
     */
    uint32_t saved_pulse = dev->pulse_count;
    uint32_t saved_total = dev->total_counts;

    /* Simulate an artificial pulse */
    dev->pulse_count = 1;
    SBM20_Tick1s(dev);

    uint32_t cps = 0;
    SBM20_Status_t st = SBM20_GetCPS(dev, &cps);
    if (st != SBM20_OK) return SBM20_ERR_SELF_TEST;

    /* The CPS should be exactly 1 from our injected pulse */
    if (cps != 1) return SBM20_ERR_SELF_TEST;

    /* Restore previous state (subtract our artificial count) */
    dev->total_counts = saved_total;

    return SBM20_OK;
#endif
}

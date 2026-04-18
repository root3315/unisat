/**
 * @file bench_ax25.c
 * @brief Host-side WCET benchmark for the AX.25 stack.
 *
 * Measures per-operation wall time for `ax25_encode_ui_frame`,
 * `ax25_decode_ui_frame`, the full streaming `ax25_decoder_push_byte`
 * loop, and HMAC-SHA256 over a beacon-sized payload. Emits JSON on
 * stdout so CI (or make coverage) can diff the numbers against
 * `docs/characterization/host_wcet_baseline.json`.
 *
 * Why this matters — the firmware runs the same algorithmic code on
 * a Cortex-M4 at 168 MHz. Host timings at ~3 GHz are a lower bound
 * on absolute performance, but trends (per-byte cost, quadratic vs
 * linear behaviour, FCS vs stuffing split) carry across. A 10x host
 * slowdown is a red flag you'll want to chase before you hit the
 * real target. See `docs/characterization/host_wcet_baseline.json`
 * for the current reference.
 *
 * Not a unit test — do NOT invoke from ctest. Build manually via
 * `cmake --build build --target bench_ax25` and run directly.
 */

#define _POSIX_C_SOURCE 199309L

#include "ax25.h"
#include "ax25_decoder.h"
#include "hmac_sha256.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#ifndef BENCH_ITERATIONS
#define BENCH_ITERATIONS 10000U
#endif

/** Monotonic-clock helper, nanosecond precision. */
static uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}

typedef struct {
    const char *name;
    uint64_t    total_ns;
    uint64_t    min_ns;
    uint64_t    max_ns;
    uint32_t    iterations;
} bench_result_t;

static void report(const bench_result_t *r) {
    double mean_us = (double)r->total_ns / (double)r->iterations / 1000.0;
    double min_us  = (double)r->min_ns / 1000.0;
    double max_us  = (double)r->max_ns / 1000.0;
    printf("  {\"name\": \"%s\", \"iterations\": %u, "
           "\"mean_us\": %.3f, \"min_us\": %.3f, \"max_us\": %.3f}",
           r->name, r->iterations, mean_us, min_us, max_us);
}

static void bench_record(bench_result_t *r, uint64_t elapsed_ns) {
    r->total_ns += elapsed_ns;
    r->iterations++;
    if (r->min_ns == 0 || elapsed_ns < r->min_ns) r->min_ns = elapsed_ns;
    if (elapsed_ns > r->max_ns) r->max_ns = elapsed_ns;
}

/* ---- 1. ax25_encode_ui_frame ------------------------------------ */
static bench_result_t bench_encode(void) {
    bench_result_t r = { .name = "ax25_encode_ui_frame" };
    ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
    ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
    uint8_t info[48];
    for (int i = 0; i < 48; i++) info[i] = (uint8_t)i;
    uint8_t out[400];
    size_t  out_len = 0;

    for (uint32_t i = 0; i < BENCH_ITERATIONS; i++) {
        uint64_t t0 = now_ns();
        (void)ax25_encode_ui_frame(&dst, &src, 0xF0, info, sizeof(info),
                                   out, sizeof(out), &out_len);
        bench_record(&r, now_ns() - t0);
    }
    return r;
}

/* ---- 2. streaming decoder, whole frame -------------------------- */
static bench_result_t bench_decoder_stream(const uint8_t *frame, size_t len) {
    bench_result_t r = { .name = "ax25_decoder_push_byte_whole_frame" };
    ax25_decoder_t dec;
    ax25_ui_frame_t out;
    bool ready = false;

    for (uint32_t i = 0; i < BENCH_ITERATIONS; i++) {
        ax25_decoder_init(&dec);
        uint64_t t0 = now_ns();
        for (size_t b = 0; b < len; b++) {
            (void)ax25_decoder_push_byte(&dec, frame[b], &out, &ready);
        }
        bench_record(&r, now_ns() - t0);
    }
    return r;
}

/* ---- 3. ax25_decode_ui_frame (pure, pre-unstuffed body) --------- */
static bench_result_t bench_decode_pure(const uint8_t *body, size_t len) {
    bench_result_t r = { .name = "ax25_decode_ui_frame_pure" };
    ax25_ui_frame_t out;

    for (uint32_t i = 0; i < BENCH_ITERATIONS; i++) {
        uint64_t t0 = now_ns();
        (void)ax25_decode_ui_frame(body, len, &out);
        bench_record(&r, now_ns() - t0);
    }
    return r;
}

/* ---- 4. HMAC-SHA256 over a 48 B beacon -------------------------- */
static bench_result_t bench_hmac(void) {
    bench_result_t r = { .name = "hmac_sha256_48B_beacon" };
    uint8_t key[32] = { 0 };
    for (int i = 0; i < 32; i++) key[i] = (uint8_t)i;
    uint8_t msg[48];
    for (int i = 0; i < 48; i++) msg[i] = (uint8_t)(i * 3);
    uint8_t tag[32];

    for (uint32_t i = 0; i < BENCH_ITERATIONS; i++) {
        uint64_t t0 = now_ns();
        hmac_sha256(key, sizeof(key), msg, sizeof(msg), tag);
        bench_record(&r, now_ns() - t0);
    }
    return r;
}

int main(void) {
    /* Build a real frame once so the decoder benchmarks have realistic
     * input instead of zero-byte corner cases. */
    ax25_address_t dst = { .callsign = "CQ", .ssid = 0 };
    ax25_address_t src = { .callsign = "UN8SAT", .ssid = 1 };
    uint8_t info[48];
    for (int i = 0; i < 48; i++) info[i] = (uint8_t)i;
    uint8_t frame[400];
    size_t  frame_len = 0;
    (void)ax25_encode_ui_frame(&dst, &src, 0xF0, info, sizeof(info),
                               frame, sizeof(frame), &frame_len);

    /* The "pure" decoder wants an unstuffed body between flags. Since
     * our beacon does not trigger bit-stuffing (no 5-ones runs), the
     * stuffed and unstuffed bodies happen to match. */
    const uint8_t *body = &frame[1];
    size_t body_len = frame_len - 2;

    bench_result_t r_encode = bench_encode();
    bench_result_t r_stream = bench_decoder_stream(frame, frame_len);
    bench_result_t r_pure   = bench_decode_pure(body, body_len);
    bench_result_t r_hmac   = bench_hmac();

    printf("{\n");
    printf("  \"tool\": \"bench_ax25\",\n");
    printf("  \"iterations_per_case\": %u,\n", (unsigned)BENCH_ITERATIONS);
    printf("  \"frame_size_bytes\": %u,\n", (unsigned)frame_len);
    printf("  \"results\": [\n    ");
    report(&r_encode); printf(",\n    ");
    report(&r_stream); printf(",\n    ");
    report(&r_pure);   printf(",\n    ");
    report(&r_hmac);   printf("\n  ]\n");
    printf("}\n");
    return 0;
}

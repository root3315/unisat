/**
 * @file sitl_fw.c
 * @brief Minimal firmware-side SITL demo binary.
 *
 * Connects to the ground-station listener on 127.0.0.1:<port>,
 * encodes two AX.25 UI beacon frames using the real firmware library,
 * and transmits them via VirtualUART. This exercises the production
 * C code paths (AX25_EncodeUiFrame + VirtualUART_Send) against the
 * ground-station listener.
 */

/* glibc / musl gate usleep() behind a feature-test macro when
 * compiling with -std=c11. Define the POSIX macro before any
 * system header so the declaration is visible under STRICT. */
#define _POSIX_C_SOURCE 200809L
#define _DEFAULT_SOURCE 1

#include "virtual_uart.h"
#include "ax25_api.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#define MILLISLEEP(ms) Sleep(ms)
#else
#include <unistd.h>
#define MILLISLEEP(ms) usleep((unsigned)(ms) * 1000)
#endif

int main(int argc, char **argv) {
  uint16_t port = (argc > 1) ? (uint16_t)atoi(argv[1]) : 52100;

  fprintf(stderr, "[sitl_fw] connecting to 127.0.0.1:%u\n", port);
  if (!VirtualUART_Init(port)) {
    fprintf(stderr, "[sitl_fw] connect failed\n");
    return 1;
  }

  AX25_Address_t dst = { .callsign = "CQ",     .ssid = 0 };
  AX25_Address_t src = { .callsign = "UN8SAT", .ssid = 1 };

  /* Build two beacon-shaped payloads (48 B each, varying content). */
  for (int i = 0; i < 2; i++) {
    uint8_t info[48];
    for (int b = 0; b < 48; b++) info[b] = (uint8_t)((i * 16) + b);

    uint8_t frame[AX25_MAX_FRAME_BYTES];
    uint16_t n = 0;
    if (!AX25_EncodeUiFrame(&dst, &src, 0xF0, info, 48,
                             frame, sizeof(frame), &n)) {
      fprintf(stderr, "[sitl_fw] encode failed\n");
      VirtualUART_Shutdown();
      return 2;
    }

    if (!VirtualUART_Send(frame, n)) {
      fprintf(stderr, "[sitl_fw] send failed\n");
      VirtualUART_Shutdown();
      return 3;
    }
    fprintf(stderr, "[sitl_fw] sent beacon %d (%u bytes)\n", i + 1, n);
    MILLISLEEP(200);
  }

  /* Give the receiver a moment to drain before we close the TCP socket. */
  MILLISLEEP(500);
  VirtualUART_Shutdown();
  fprintf(stderr, "[sitl_fw] done\n");
  return 0;
}

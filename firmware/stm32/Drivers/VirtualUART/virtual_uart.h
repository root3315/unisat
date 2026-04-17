/**
 * @file virtual_uart.h
 * @brief SIM-only TCP shim replacing HAL UART for SITL demos.
 *
 * Connects to the ground station on 127.0.0.1:<port> as a TCP client.
 * Bytes written go out as TCP; bytes arriving on the socket are
 * delivered to the caller via VirtualUART_Recv. Only compiled when
 * SIMULATION_MODE is defined (see spec §4.3).
 */
#ifndef VIRTUAL_UART_H
#define VIRTUAL_UART_H

#include <stdint.h>
#include <stdbool.h>

/** Connect to 127.0.0.1:port. Returns true on success. */
bool VirtualUART_Init(uint16_t port);

/** Close the TCP socket. Safe to call multiple times. */
void VirtualUART_Shutdown(void);

/** Send @p len bytes; returns true if all bytes made it to the kernel. */
bool VirtualUART_Send(const uint8_t *data, uint16_t len);

/** Non-blocking poll. Returns number of bytes read (0 if none). */
int VirtualUART_Recv(uint8_t *buf, int max_bytes);

#endif /* VIRTUAL_UART_H */

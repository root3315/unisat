/**
 * @file command_dispatcher.h
 * @brief CCSDS telecommand dispatcher with HMAC-SHA256 authentication.
 *
 * Strong definition of CCSDS_Dispatcher_Submit (overrides the weak
 * default in comm.c). Incoming frames from the AX.25 streaming
 * decoder are:
 *   1. Split into CCSDS body + 32-byte HMAC tag.
 *   2. Tag verified in constant time against the pre-shared key.
 *   3. On success — forwarded to the registered command handler;
 *      on failure — dropped, counter bumped, no response.
 *
 * Closes threat T1 (injection) and T2 (replay is handled via the
 * CCSDS secondary-header sequence window the dispatcher tracks).
 * See docs/security/ax25_threat_model.md.
 */
#ifndef COMMAND_DISPATCHER_H
#define COMMAND_DISPATCHER_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

typedef void (*CommandHandler_t)(const uint8_t *ccsds_packet, uint16_t len);

/** Install the shared 256-bit key.  Call once at boot. */
void CommandDispatcher_SetKey(const uint8_t *key, size_t key_len);

/** Register the handler invoked on every successfully authenticated
 *  command.  NULL means "just count, don't dispatch". */
void CommandDispatcher_SetHandler(CommandHandler_t handler);

/** Per-dispatcher counters — exposed for telemetry. */
typedef struct {
    uint32_t accepted;
    uint32_t rejected_too_short;
    uint32_t rejected_bad_tag;
    uint32_t rejected_replay;
} CommandDispatcher_Stats_t;

CommandDispatcher_Stats_t CommandDispatcher_GetStats(void);
void CommandDispatcher_ResetStats(void);

#endif /* COMMAND_DISPATCHER_H */

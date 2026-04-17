/**
 * @file virtual_uart.c
 * @brief Cross-platform TCP loopback shim (SIM-only).
 *
 * Works on Linux/macOS via BSD sockets and on Windows via Winsock.
 * The socket is non-blocking after connect so VirtualUART_Recv returns
 * immediately when no bytes are buffered.
 */

#include "virtual_uart.h"
#include <string.h>

#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
typedef SOCKET sock_t;
#define SOCK_INVALID ((sock_t)INVALID_SOCKET)
#define CLOSE_SOCK closesocket
#else
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
typedef int sock_t;
#define SOCK_INVALID (-1)
#define CLOSE_SOCK close
#endif

static sock_t s_fd = SOCK_INVALID;

bool VirtualUART_Init(uint16_t port) {
#ifdef _WIN32
  WSADATA wsa;
  if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return false;
#endif
  s_fd = socket(AF_INET, SOCK_STREAM, 0);
  if (s_fd == SOCK_INVALID) return false;

  struct sockaddr_in addr;
  memset(&addr, 0, sizeof(addr));
  addr.sin_family = AF_INET;
  addr.sin_port = htons(port);
  inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr);

  if (connect(s_fd, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
    CLOSE_SOCK(s_fd);
    s_fd = SOCK_INVALID;
    return false;
  }

  /* Switch to non-blocking for the poll-based Recv path. */
#ifdef _WIN32
  u_long mode = 1;
  ioctlsocket(s_fd, FIONBIO, &mode);
#else
  int flags = fcntl(s_fd, F_GETFL, 0);
  fcntl(s_fd, F_SETFL, flags | O_NONBLOCK);
#endif
  return true;
}

void VirtualUART_Shutdown(void) {
  if (s_fd != SOCK_INVALID) {
    CLOSE_SOCK(s_fd);
    s_fd = SOCK_INVALID;
  }
#ifdef _WIN32
  WSACleanup();
#endif
}

bool VirtualUART_Send(const uint8_t *data, uint16_t len) {
  if (s_fd == SOCK_INVALID) return false;
  int n = send(s_fd, (const char *)data, len, 0);
  return n == (int)len;
}

int VirtualUART_Recv(uint8_t *buf, int max_bytes) {
  if (s_fd == SOCK_INVALID) return 0;
  int n = recv(s_fd, (char *)buf, max_bytes, 0);
  return n < 0 ? 0 : n;
}

"""IoT Relay Payload — Store-and-forward message relay."""

import time
from dataclasses import dataclass


@dataclass
class IoTMessage:
    """Single IoT message for relay."""
    timestamp: float
    source_id: str
    payload: bytes
    rssi: int
    forwarded: bool = False


class IoTRelayPayload:
    """LoRa-based IoT message collection and forwarding."""

    def __init__(self, frequency_mhz: float = 868.0) -> None:
        self.frequency_mhz = frequency_mhz
        self.messages: list[IoTMessage] = []
        self.active = False

    def initialize(self) -> bool:
        self.active = True
        return True

    def receive_message(self, source_id: str, payload: bytes, rssi: int) -> IoTMessage:
        msg = IoTMessage(time.time(), source_id, payload, rssi)
        self.messages.append(msg)
        return msg

    def get_pending_messages(self) -> list[IoTMessage]:
        return [m for m in self.messages if not m.forwarded]

    def mark_forwarded(self, count: int) -> int:
        forwarded = 0
        for msg in self.messages:
            if not msg.forwarded and forwarded < count:
                msg.forwarded = True
                forwarded += 1
        return forwarded

    def shutdown(self) -> None:
        self.active = False

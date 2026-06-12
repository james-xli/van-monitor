"""
Anker Solix C1000 Gen 2 BLE protocol (pure Python, no Bluetooth here).

WHY THIS EXISTS
---------------
The `SolixBLE` library negotiates with older Anker units (C300X, C1000 Gen 1,
Prime chargers) by replaying a *fixed* handshake with a hardcoded private key.
The C1000 *Gen 2* firmware rejects that. It requires:

  1. A live ECDH (P-256) key exchange to derive a per-session AES key, and
  2. A one-time physical button press on the station to authorize the client.

This module is a direct port of community C++ code (NimBLE / mbedTLS, see
SolixProtocol.cpp) that is known to work on the Gen 2. It contains ONLY the
protocol/crypto logic. The Bluetooth plumbing lives in
`van_monitor/collectors/anker_g2.py`, which feeds bytes in and writes bytes out.

HOW THE HANDSHAKE WORKS (high level)
------------------------------------
Every BLE packet looks like:

    FF 09 <len_lo> <len_hi> <pattern:3> <command:2> <payload...> <xor_checksum>

We start by sending a "negotiation init" (command 4001). The station replies
with a sequence of commands; for each one we send the next response:

    4801 -> 4003
    4803 -> 4029        (station tells us its MTU + capabilities)
    4829 -> 4005        (station tells us its serial number + firmware)
    4805 -> 4021        (we send our ECDH public key)
    4821 -> 4022        (station sends its public key; we derive shared secret)
    4822 -> 4027        (we send our client UUID)
    4827 -> (first time) "PRESS THE BUTTON", then after the press -> 4023
            (already paired) -> negotiation complete
    4823 -> negotiation complete

The first few messages are encrypted with a *fixed* negotiation key. After the
ECDH step, messages switch to the *session* key (derived from the shared
secret). Once negotiated we send a "realtime trigger" (command 4100) and the
station streams telemetry packets, which we decrypt and parse into
`SolixTelemetry`.

KEY ASSUMPTION: the same client UUID, once authorized via the button press, is
remembered by the station. So we persist the UUID to disk and reuse it; the
button press is only needed the very first time.
"""

from __future__ import annotations

import logging
import time
import uuid as uuid_module
from dataclasses import dataclass, field

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# GATT characteristics (same as SolixBLE; confirmed against the Gen 2).
UUID_TELEMETRY = "8c850003-0302-41c5-b46e-cf057c562025"  # notify (station -> us)
UUID_COMMAND = "8c850002-0302-41c5-b46e-cf057c562025"  # write (us -> station)
UUID_IDENTIFIER = "0000ff09-0000-1000-8000-00805f9b34fb"  # advertised service

# Fixed crypto material used for the *negotiation* phase (before ECDH completes).
# These come straight from the working C++ reference and are baked into the
# Anker firmware. Do not change unless Anker changes their protocol.
_NEG_KEY = bytes.fromhex("b8ff7422955d4eb6d554a2c470280559")
_NEG_NONCE = bytes.fromhex("6ba3e3f2f3a60f2971ce5d1f")
_AAD = bytes.fromhex("3322110077665544bbaa9988ffeeddcc")

# Telemetry commands the station can send (after negotiation). Anything in this
# set is treated as a (possibly fragmented) telemetry packet.
_TELEMETRY_COMMANDS = {0xC402, 0x4300, 0xC405, 0xC421, 0xC840, 0xC900}


@dataclass
class SolixTelemetry:
    """One decoded telemetry snapshot. -1 means "field not present"."""

    serial_number: str = ""
    part_number: str = ""
    temperature_c: int = -1
    battery_percent: int = -1
    battery_health: int = -1
    total_power_out: int = -1
    ac_power_in: int = -1
    ac_output_on: bool = False
    ac_power_out: int = -1
    solar_power_in: int = -1
    dc_output_on: bool = False
    dc_power_out: int = -1
    usb_c1_power: int = -1
    usb_c2_power: int = -1
    usb_c3_power: int = -1
    usb_a1_power: int = -1
    max_battery_percent: int = -1
    min_battery_percent: int = -1
    net_watts: int = 0
    valid: bool = False


@dataclass
class HandleResult:
    """What the driver should do after we process one inbound packet."""

    outbound_command: bytes | None = None
    outbound_requires_response: bool = True
    negotiation_complete: bool = False
    telemetry: SolixTelemetry | None = None
    telemetry_updated: bool = False
    waiting_for_button: bool = False
    debug_message: str = ""


# ---------------------------------------------------------------------------
# Small byte helpers
# ---------------------------------------------------------------------------


def _xor_checksum(data: bytes) -> int:
    value = 0
    for byte in data:
        value ^= byte
    return value


def _le32(value: int) -> bytes:
    return (value & 0xFFFFFFFF).to_bytes(4, "little")


def _hex(data: bytes) -> str:
    return data.hex()


class SolixProtocol:
    """
    Stateful protocol engine. Create one per BLE connection.

    Typical use from the driver:

        proto = SolixProtocol(client_uuid=saved_uuid)
        write(proto.build_negotiation_init())          # kick things off
        # ... on every notification:
        result = proto.handle_notification(data)
        if result.outbound_command: write(result.outbound_command)
        if result.telemetry_updated and result.telemetry.valid: use it
    """

    def __init__(self, client_uuid: str | None = None) -> None:
        self._client_uuid = client_uuid
        self.reset()

    # -- lifecycle ----------------------------------------------------------

    def reset(self) -> None:
        self._negotiated = False
        self._fragments: dict[int, dict] = {}
        self._shared_secret: bytes | None = None
        self._ephemeral_key: ec.EllipticCurvePrivateKey | None = None
        self._session_timestamp = 0
        self._session_uuid = self._client_uuid or self._generate_uuid()
        self._station_sn = ""
        self._station_mtu = 0
        self._station_cap_a3 = 0
        self._station_cap_a4 = 0
        self._station_cap_a5 = 0
        self._waiting_for_button = False

    def _init_session(self) -> None:
        # The station uses this timestamp for replay protection. Any current-ish
        # unix time works; it just has to be consistent within the session.
        self._session_timestamp = int(time.time())

    @staticmethod
    def _generate_uuid() -> str:
        # uuid4 already sets the version (4) and variant bits the station wants.
        return str(uuid_module.uuid4())

    @property
    def client_uuid(self) -> str:
        return self._session_uuid

    def is_negotiated(self) -> bool:
        return self._negotiated

    def is_waiting_for_button(self) -> bool:
        return self._waiting_for_button

    def has_session_key(self) -> bool:
        return self._shared_secret is not None and any(self._shared_secret)

    # -- outbound: kick off negotiation ------------------------------------

    def build_negotiation_init(self) -> bytes:
        """First packet we send. Resets the session timestamp."""
        self._init_session()
        params = {0xA1: _le32(self._session_timestamp)}
        payload = self._build_tlv(params)
        encrypted = self._encrypt_negotiation(payload)
        logger.debug(
            "[NEG] TX 4001 init ts=%08x uuid=%s",
            self._session_timestamp,
            self._session_uuid,
        )
        return self._build_packet(b"\x03\x00\x01", b"\x40\x01", encrypted)

    def build_realtime_trigger(self, elapsed_seconds: int = 1) -> bytes:
        """
        Ask the station to start streaming telemetry. Only valid once the
        session key exists. Safe to re-send periodically if telemetry stalls.
        """
        if not self._negotiated or not self.has_session_key():
            return b""
        request_timestamp = self._session_timestamp + elapsed_seconds
        payload = bytes(
            [
                0xA1, 0x01, 0x21,
                0xA2, 0x06, 0x04, 0x01, 0x00, 0x03, 0x13, 0x00,
                0xFE, 0x04,
            ]
        ) + _le32(request_timestamp)
        return self._build_packet(b"\x03\x00\x0f", b"\x41\x00", self._encrypt_session(payload))

    # -- inbound: process one notification ---------------------------------

    def handle_notification(self, data: bytes) -> HandleResult:
        try:
            pattern, command, payload = self._split_packet(data)
        except ValueError as exc:
            return HandleResult(debug_message=f"bad packet: {exc}")

        pattern_value = int.from_bytes(pattern, "big")
        command_value = int.from_bytes(command, "big")

        # Negotiation packets.
        if pattern_value in (0x030001, 0x030101):
            return self._process_negotiation(pattern_value, command_value, payload)

        # Telemetry / post-negotiation packets.
        if pattern_value in (0x03010F, 0x030111):
            if command_value in _TELEMETRY_COMMANDS:
                return self._process_telemetry(command_value, payload)
            # Unknown encrypted command: try to decrypt + parse anyway.
            return self._process_unknown_encrypted(command_value, command, payload)

        return HandleResult()

    # -- negotiation state machine -----------------------------------------

    def _process_negotiation(self, pattern_value: int, command_value: int, payload: bytes) -> HandleResult:
        result = HandleResult()

        if command_value == 0x4801:
            params = {
                0xA1: _le32(self._session_timestamp),
                0xA3: b"\x20",
                0xA4: b"\x00\xf0",
            }
            tlv = self._build_tlv(params)
            result.outbound_command = self._build_packet(
                b"\x03\x00\x01", b"\x40\x03", self._encrypt_negotiation(tlv)
            )
            result.debug_message = "4801 -> TX 4003"

        elif command_value == 0x4803:
            info = ""
            try:
                decrypted = self._decrypt_negotiation(payload)
                params = self._parse_tlv(decrypted)
                mtu = params.get(0xA2)
                if mtu and len(mtu) >= 2:
                    self._station_mtu = mtu[0] | (mtu[1] << 8)
                    info = f" MTU={self._station_mtu}"
                self._station_cap_a3 = self._first_byte(params, 0xA3)
                self._station_cap_a4 = self._first_byte(params, 0xA4)
                self._station_cap_a5 = self._first_byte(params, 0xA5)
            except Exception:
                info = " (decrypt failed)"
            tlv = self._build_tlv({0xA1: _le32(self._session_timestamp)})
            result.outbound_command = self._build_packet(
                b"\x03\x00\x01", b"\x40\x29", self._encrypt_negotiation(tlv)
            )
            result.debug_message = f"4803{info} -> TX 4029"

        elif command_value == 0x4829:
            info = ""
            try:
                decrypted = self._decrypt_negotiation(payload)
                params = self._parse_tlv(decrypted)
                sn = params.get(0xA4)
                if sn:
                    self._station_sn = bytes(sn).split(b"\x00")[0].decode("latin-1")
                    info = f" SN={self._station_sn}"
            except Exception:
                info = " (decrypt failed)"
            echo_mtu = bytes([self._station_mtu & 0xFF, (self._station_mtu >> 8) & 0xFF])
            params = {
                0xA1: _le32(self._session_timestamp),
                0xA3: b"\x20",
                0xA4: echo_mtu,
                0xA5: bytes([self._station_cap_a3]),
                0xA6: bytes([self._station_cap_a5]),
            }
            tlv = self._build_tlv(params)
            result.outbound_command = self._build_packet(
                b"\x03\x00\x01", b"\x40\x05", self._encrypt_negotiation(tlv)
            )
            result.debug_message = f"4829{info} -> TX 4005 echo MTU={self._station_mtu}"

        elif command_value == 0x4805:
            try:
                pubkey_payload = self._build_local_public_key_payload()
                result.outbound_command = self._build_packet(
                    b"\x03\x00\x01", b"\x40\x21", self._encrypt_negotiation(pubkey_payload)
                )
                result.debug_message = "4805 -> TX 4021 (ECDH pubkey)"
            except Exception as exc:
                result.debug_message = f"4805 -> 4021 FAILED: {exc}"

        elif command_value == 0x4821:
            try:
                decrypted = self._decrypt_negotiation(payload)
                params = self._parse_tlv(decrypted)
                peer_key = params.get(0xA1)
                if not peer_key:
                    raise ValueError("missing peer public key in 4821")
                self._derive_shared_secret(bytes(peer_key))

                tz_string = b"GMT0BST,M3.5.0/1,M10.5.0"
                params_out = {
                    0xA1: _le32(self._session_timestamp + 1),
                    0xA3: _le32(0xFFFFE3E0),
                    0xA5: tz_string,
                }
                tlv = self._build_tlv(params_out)
                # From here on, use the *session* key.
                result.outbound_command = self._build_packet(
                    b"\x03\x00\x01", b"\x40\x22", self._encrypt_session(tlv)
                )
                result.debug_message = "4821 ECDH ok -> TX 4022 (TZ)"
            except Exception as exc:
                result.debug_message = f"4821 ECDH FAILED: {exc}"

        elif command_value == 0x4822:
            uuid_bytes = self._session_uuid.encode("ascii")
            params = {
                0xA1: _le32(self._session_timestamp + 1),
                0xA2: uuid_bytes,
            }
            tlv = self._build_tlv(params)
            result.outbound_command = self._build_packet(
                b"\x03\x00\x01", b"\x40\x27", self._encrypt_session(tlv)
            )
            result.debug_message = f"4822 -> TX 4027 UUID={self._session_uuid}"

        elif command_value == 0x4827:
            result = self._process_4827(pattern_value, payload)

        elif command_value == 0x4823:
            self._negotiated = True
            self._waiting_for_button = False
            result.negotiation_complete = True
            trigger = self.build_realtime_trigger(1)
            if trigger:
                result.outbound_command = trigger
                result.outbound_requires_response = False
            result.debug_message = "4823 token-ack -> NEGOTIATED -> TX 4100 trigger"

        return result

    def _process_4827(self, pattern_value: int, payload: bytes) -> HandleResult:
        result = HandleResult()

        # Try to decrypt the payload (used to detect the "authorized" marker).
        decrypted_ok = False
        plaintext = b""
        try:
            plaintext = self._decrypt_session(payload)
            decrypted_ok = True
        except Exception:
            pass

        if pattern_value == 0x030101:
            # This arrives AFTER the user pressed the physical button.
            uuid_bytes = self._session_uuid.encode("ascii")
            sn = (self._station_sn or "?").encode("latin-1")
            params = {
                0xA1: _le32(self._session_timestamp + 1),
                0xA2: uuid_bytes,
                0xA3: sn,
                0xA4: b"\x00",
            }
            tlv = self._build_tlv(params)
            result.outbound_command = self._build_packet(
                b"\x03\x00\x01", b"\x40\x23", self._encrypt_session(tlv)
            )
            self._waiting_for_button = False
            result.debug_message = "4827 (post-button) -> TX 4023"
            return result

        # pattern 0x030001: either already authorized, or button required.
        authorized = decrypted_ok and len(plaintext) == 1 and plaintext[0] == 0x00
        if authorized:
            self._negotiated = True
            self._waiting_for_button = False
            result.negotiation_complete = True
            trigger = self.build_realtime_trigger(1)
            if trigger:
                result.outbound_command = trigger
                result.outbound_requires_response = False
            result.debug_message = "4827 authorized -> NEGOTIATED -> TX 4100 trigger"
        else:
            self._waiting_for_button = True
            result.waiting_for_button = True
            result.debug_message = (
                "4827 first-ack -> PRESS THE PHYSICAL BUTTON on the Anker "
                "(180s window) to authorize this device"
            )
        return result

    # -- telemetry ----------------------------------------------------------

    def _process_telemetry(self, command_value: int, payload: bytes) -> HandleResult:
        if not self._negotiated or not self.has_session_key() or not payload:
            return HandleResult()

        assembled = self._reassemble(command_value, payload)
        if assembled is None:
            return HandleResult()  # waiting for more fragments

        try:
            decrypted = self._decrypt_session(assembled)
            params = self._parse_tlv(decrypted)
            telemetry = self._parse_telemetry(params)
        except Exception as exc:
            return HandleResult(debug_message=f"telemetry {command_value:04x} decode failed: {exc}")

        result = HandleResult(telemetry=telemetry, telemetry_updated=True)
        if not telemetry.valid:
            result.debug_message = (
                f"telemetry {command_value:04x} parsed but invalid; "
                f"decrypted={_hex(decrypted)}"
            )
        return result

    def _process_unknown_encrypted(self, command_value: int, command: bytes, payload: bytes) -> HandleResult:
        if not self.has_session_key():
            return HandleResult()
        candidate = payload
        try:
            try:
                decrypted = self._decrypt_session(candidate)
            except Exception:
                # Some packets drop the leading command byte; retry with it.
                if (len(candidate) % 16) != 15:
                    raise
                candidate = bytes([command[1]]) + candidate
                decrypted = self._decrypt_session(candidate)
            params = self._parse_tlv(decrypted)
            telemetry = self._parse_telemetry(params)
            return HandleResult(
                telemetry=telemetry,
                telemetry_updated=telemetry.valid,
                debug_message=f"unknown cmd {command_value:04x} decrypted={_hex(decrypted)}",
            )
        except Exception as exc:
            return HandleResult(debug_message=f"unknown cmd {command_value:04x} failed: {exc}")

    def _reassemble(self, command_value: int, payload: bytes) -> bytes | None:
        """
        Telemetry can be split across multiple BLE notifications. Returns the
        full payload once all fragments arrive, else None.
        """
        # Command 0xC840 uses a simple "2 fixed fragments" scheme.
        if command_value == 0xC840:
            acc = self._fragments.setdefault(command_value, {"total": 2, "parts": {}})
            index = len(acc["parts"]) + 1
            acc["parts"][index] = bytes(payload[1:]) if len(payload) > 1 else b""
            if len(acc["parts"]) < acc["total"]:
                return None
            assembled = acc["parts"].get(1, b"") + acc["parts"].get(2, b"")
            self._fragments.pop(command_value, None)
            return assembled

        # Everything else: first byte is (index << 4 | total).
        header = payload[0]
        index = (header >> 4) & 0x0F
        total = header & 0x0F

        if total > 1:
            acc = self._fragments.get(command_value)
            if acc is None or index == 1 or acc["total"] != total:
                acc = {"total": total, "parts": {}}
                self._fragments[command_value] = acc
            acc["parts"][index] = bytes(payload[1:])
            if len(acc["parts"]) < total:
                return None
            assembled = b""
            for i in range(1, total + 1):
                if i not in acc["parts"]:
                    return None
                assembled += acc["parts"][i]
            self._fragments.pop(command_value, None)
            return assembled

        return bytes(payload[1:])

    def _parse_telemetry(self, params: dict[int, bytes]) -> SolixTelemetry:
        t = SolixTelemetry()
        t.serial_number = self._param_str(params, 0xA2, 3, 20)
        t.part_number = self._param_str(params, 0xA2, 22, 27)
        t.temperature_c = self._param_int(params, 0xA5, 1, 2, signed=True)
        t.battery_percent = self._param_int(params, 0xA5, 3, 4)
        t.battery_health = self._param_int(params, 0xA5, 4, 5)
        t.total_power_out = self._param_int(params, 0xA6, 1, 3)
        t.ac_power_in = self._param_int(params, 0xA6, 3, 5)
        t.ac_output_on = self._param_int(params, 0xA7, 1, 2) == 1
        t.ac_power_out = self._param_int(params, 0xA7, 2, 4)
        t.solar_power_in = self._param_int(params, 0xA8, 2)
        t.usb_c1_power = self._param_int(params, 0xAA, 2)
        t.usb_c2_power = self._param_int(params, 0xAB, 2)
        t.usb_c3_power = self._param_int(params, 0xAC, 2)
        t.usb_a1_power = self._param_int(params, 0xAE, 2)
        t.dc_output_on = self._param_int(params, 0xB2, 1, 2) == 1
        t.dc_power_out = self._param_int(params, 0xB2, 2)
        t.max_battery_percent = self._param_int(params, 0xD9, 4, 5)
        t.min_battery_percent = self._param_int(params, 0xD9, 5, 6)

        ac_in = max(t.ac_power_in, 0)
        solar_in = max(t.solar_power_in, 0)
        out = max(t.total_power_out, 0)
        t.net_watts = ac_in + solar_in - out
        t.valid = t.battery_percent >= 0
        return t

    # -- crypto -------------------------------------------------------------

    def _encrypt_negotiation(self, plaintext: bytes) -> bytes:
        return AESGCM(_NEG_KEY).encrypt(_NEG_NONCE, plaintext, _AAD)

    def _decrypt_negotiation(self, payload: bytes) -> bytes:
        if len(payload) < 16:
            raise ValueError("negotiation payload too short")
        return AESGCM(_NEG_KEY).decrypt(_NEG_NONCE, payload, _AAD)

    def _encrypt_session(self, plaintext: bytes) -> bytes:
        key, nonce = self._session_key_nonce()
        return AESGCM(key).encrypt(nonce, plaintext, _AAD)

    def _decrypt_session(self, payload: bytes) -> bytes:
        if len(payload) < 16:
            raise ValueError("session payload too short")
        key, nonce = self._session_key_nonce()
        return AESGCM(key).decrypt(nonce, payload, _AAD)

    def _session_key_nonce(self) -> tuple[bytes, bytes]:
        if not self.has_session_key():
            raise ValueError("no session key derived yet")
        # The 32-byte ECDH secret doubles as key (first 16) and nonce (next 12).
        return self._shared_secret[0:16], self._shared_secret[16:28]

    def _build_local_public_key_payload(self) -> bytes:
        """Generate our ephemeral ECDH key and return its public half as TLV."""
        self._ephemeral_key = ec.generate_private_key(ec.SECP256R1())
        numbers = self._ephemeral_key.public_key().public_numbers()
        x = numbers.x.to_bytes(32, "big")
        y = numbers.y.to_bytes(32, "big")
        # TLV: key 0xA1, length 0x40 (64), then the 64-byte X||Y public key.
        return bytes([0xA1, 0x40]) + x + y

    def _derive_shared_secret(self, peer_xy: bytes) -> None:
        if self._ephemeral_key is None:
            raise ValueError("no ephemeral key (4805/4021 step missing)")
        if len(peer_xy) != 64:
            raise ValueError(f"unexpected peer key length {len(peer_xy)}")
        peer_point = b"\x04" + peer_xy  # 0x04 = uncompressed point prefix
        peer_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), peer_point)
        self._shared_secret = self._ephemeral_key.exchange(ec.ECDH(), peer_key)

    # -- packet framing -----------------------------------------------------

    def _build_packet(self, pattern: bytes, command: bytes, payload: bytes) -> bytes:
        length = 2 + 2 + len(pattern) + len(command) + len(payload) + 1
        packet = bytearray()
        packet += b"\xff\x09"
        packet += bytes([length & 0xFF, (length >> 8) & 0xFF])
        packet += pattern
        packet += command
        packet += payload
        packet.append(_xor_checksum(bytes(packet)))
        return bytes(packet)

    def _split_packet(self, data: bytes) -> tuple[bytes, bytes, bytes]:
        if len(data) < 8:
            raise ValueError("packet too short")
        if data[0] != 0xFF or data[1] != 0x09:
            raise ValueError("header mismatch")
        encoded_length = data[2] | (data[3] << 8)
        if encoded_length != len(data):
            raise ValueError(f"length mismatch ({encoded_length} != {len(data)})")
        if _xor_checksum(data[:-1]) != data[-1]:
            raise ValueError("checksum mismatch")
        pattern = data[4:7]
        command = data[7:9]
        payload = data[9:-1]
        return pattern, command, payload

    # -- TLV (tag-length-value) parameter encoding --------------------------

    @staticmethod
    def _build_tlv(params: dict[int, bytes]) -> bytes:
        """Encode params in ascending key order (matches the station)."""
        out = bytearray()
        for key in sorted(params):
            value = params[key]
            out.append(key)
            if len(value) > 0xFF:
                out.append(0xFF)
                out.append((len(value) >> 8) & 0xFF)
                out.append(len(value) & 0xFF)
            else:
                out.append(len(value))
            out += value
        return bytes(out)

    @staticmethod
    def _parse_tlv(payload: bytes) -> dict[int, bytes]:
        params: dict[int, bytes] = {}
        index = 0
        # A leading 0x00 status byte sometimes prefixes the parameter list.
        if payload and payload[0] == 0x00:
            index = 1
        while index < len(payload):
            key = payload[index]
            index += 1
            if index >= len(payload):
                params[key] = b""
                break
            length = payload[index]
            index += 1
            if index + length > len(payload):
                raise ValueError("TLV parameter exceeds payload")
            params[key] = bytes(payload[index : index + length])
            index += length
        return params

    @staticmethod
    def _first_byte(params: dict[int, bytes], key: int) -> int:
        value = params.get(key)
        return value[0] if value else 0

    @staticmethod
    def _param_int(
        params: dict[int, bytes],
        key: int,
        begin: int,
        end: int | None = None,
        *,
        signed: bool = False,
    ) -> int:
        value = params.get(key)
        if value is None or begin >= len(value):
            return -1
        stop = len(value) if (end is None or end > len(value)) else end
        if stop <= begin:
            return -1
        return int.from_bytes(value[begin:stop], "little", signed=signed)

    @staticmethod
    def _param_str(params: dict[int, bytes], key: int, begin: int, end: int | None = None) -> str:
        value = params.get(key)
        if value is None or begin >= len(value):
            return ""
        stop = len(value) if (end is None or end > len(value)) else end
        if stop <= begin:
            return ""
        chunk = bytes(value[begin:stop]).split(b"\x00")[0]
        return chunk.decode("latin-1", errors="replace")

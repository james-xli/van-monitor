#!/usr/bin/env python3
"""
Offline self-test for the Anker C1000 Gen 2 protocol port.

This does NOT touch Bluetooth. It checks the pure-Python protocol logic
(packet framing, TLV encoding, ECDH key agreement, AES-GCM, telemetry parsing)
so you can confirm the port is internally consistent before testing on the van.

Run it anywhere Python + cryptography are installed:

    python scripts/test_anker_protocol.py

Every check prints PASS / FAIL; exit code is non-zero if anything fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.hazmat.primitives.asymmetric import ec

from van_monitor.anker_g2_protocol import SolixProtocol

_failures = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global _failures
    status = "PASS" if condition else "FAIL"
    if not condition:
        _failures += 1
    line = f"[{status}] {name}"
    if detail:
        line += f"  ({detail})"
    print(line)


def test_packet_roundtrip() -> None:
    proto = SolixProtocol()
    pattern = b"\x03\x00\x0f"
    command = b"\x41\x00"
    payload = bytes(range(10))
    packet = proto._build_packet(pattern, command, payload)

    check("packet header is FF 09", packet[0] == 0xFF and packet[1] == 0x09)
    out_pattern, out_command, out_payload = proto._split_packet(packet)
    check("packet pattern round-trips", out_pattern == pattern)
    check("packet command round-trips", out_command == command)
    check("packet payload round-trips", out_payload == payload)

    # Corrupt the checksum and confirm it is rejected.
    bad = bytearray(packet)
    bad[-1] ^= 0xFF
    try:
        proto._split_packet(bytes(bad))
        check("bad checksum rejected", False)
    except ValueError:
        check("bad checksum rejected", True)


def test_tlv_roundtrip() -> None:
    params = {0xA1: b"\x01\x02\x03\x04", 0xA3: b"\x20", 0xA4: b"\x00\xf0"}
    encoded = SolixProtocol._build_tlv(params)
    decoded = SolixProtocol._parse_tlv(encoded)
    check("TLV round-trips", decoded == params, f"{decoded}")

    # Keys must be emitted in ascending order (the station expects this).
    check("TLV keys ascending", encoded[0] == 0xA1)

    # A leading 0x00 status byte must be skipped on parse.
    decoded_status = SolixProtocol._parse_tlv(b"\x00" + encoded)
    check("TLV leading 0x00 skipped", decoded_status == params)


def test_ecdh_and_session_crypto() -> None:
    proto = SolixProtocol()

    # Our side generates an ephemeral key and exports its public half.
    pubkey_tlv = proto._build_local_public_key_payload()
    check("pubkey TLV tag/len", pubkey_tlv[0] == 0xA1 and pubkey_tlv[1] == 0x40)
    check("pubkey TLV length", len(pubkey_tlv) == 66)

    # Simulate the station: it has its own P-256 key.
    station_key = ec.generate_private_key(ec.SECP256R1())
    station_nums = station_key.public_key().public_numbers()
    station_xy = station_nums.x.to_bytes(32, "big") + station_nums.y.to_bytes(32, "big")

    # We derive the shared secret from the station's public key...
    proto._derive_shared_secret(station_xy)

    # ...and the station derives the same secret from our public key.
    our_xy = pubkey_tlv[2:]
    our_pub = ec.EllipticCurvePublicKey.from_encoded_point(
        ec.SECP256R1(), b"\x04" + our_xy
    )
    station_secret = station_key.exchange(ec.ECDH(), our_pub)

    check("ECDH secrets match", proto._shared_secret == station_secret)
    check("shared secret is 32 bytes", len(proto._shared_secret) == 32)

    # Session AES-GCM should round-trip with the derived key.
    plaintext = b"hello anker gen2"
    encrypted = proto._encrypt_session(plaintext)
    decrypted = proto._decrypt_session(encrypted)
    check("session AES-GCM round-trips", decrypted == plaintext)


def test_telemetry_parse() -> None:
    """Craft a telemetry packet exactly as the station would and decode it."""
    proto = SolixProtocol()
    # Force a negotiated session with a known shared secret.
    proto._negotiated = True
    proto._shared_secret = bytes(range(32))

    battery = 87
    ac_in = 320
    solar_in = 150
    total_out = 45

    params = {
        0xA2: b"\x00\x00\x00" + b"SN1234567890" + b"\x00" * 5,  # serial at [3:]
        0xA5: bytes([0x00, 25, 0x00, battery, 100]),  # temp@1, batt@3, health@4
        0xA6: bytes([0x00]) + total_out.to_bytes(2, "little") + ac_in.to_bytes(2, "little"),
        0xA8: bytes([0x00, 0x00]) + solar_in.to_bytes(2, "little"),
    }
    tlv = SolixProtocol._build_tlv(params)
    encrypted_blob = proto._encrypt_session(tlv)

    # Single-fragment telemetry: payload = [header 0x11] + encrypted blob.
    ble_payload = bytes([0x11]) + encrypted_blob
    packet = proto._build_packet(b"\x03\x01\x0f", b"\xc9\x00", ble_payload)

    result = proto.handle_notification(packet)
    tel = result.telemetry
    check("telemetry produced", tel is not None and result.telemetry_updated)
    if tel is not None:
        check("battery percent", tel.battery_percent == battery, f"{tel.battery_percent}")
        check("ac power in", tel.ac_power_in == ac_in, f"{tel.ac_power_in}")
        check("solar power in", tel.solar_power_in == solar_in, f"{tel.solar_power_in}")
        check("total power out", tel.total_power_out == total_out, f"{tel.total_power_out}")
        check("watts in (ac+solar)", (tel.ac_power_in + tel.solar_power_in) == ac_in + solar_in)
        check("net watts", tel.net_watts == ac_in + solar_in - total_out, f"{tel.net_watts}")
        check("serial parsed", tel.serial_number == "SN1234567890", tel.serial_number)
        check("telemetry valid flag", tel.valid)


def test_negotiation_init() -> None:
    proto = SolixProtocol(client_uuid="12345678-1234-4123-8123-1234567890ab")
    init = proto.build_negotiation_init()
    pattern, command, _payload = proto._split_packet(init)
    check("init pattern 030001", pattern == b"\x03\x00\x01")
    check("init command 4001", command == b"\x40\x01")
    check("client uuid preserved", proto.client_uuid == "12345678-1234-4123-8123-1234567890ab")


def main() -> int:
    print("=== Anker C1000 Gen 2 protocol self-test (no Bluetooth) ===\n")
    test_packet_roundtrip()
    test_tlv_roundtrip()
    test_ecdh_and_session_crypto()
    test_telemetry_parse()
    test_negotiation_init()
    print()
    if _failures:
        print(f"{_failures} check(s) FAILED")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

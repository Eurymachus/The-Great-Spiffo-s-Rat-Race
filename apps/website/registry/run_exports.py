import base64
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone


PREFIX = "TGSRR1.LZ1."
GENESIS_HASH = "0" * 64
MAX_ENCODED_CHARACTERS = 24 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 16 * 1024 * 1024
ENVELOPE_RE = re.compile(r"^TGSRR1\.LZ1\.([A-Za-z0-9_-]+)\.([0-9a-f]{64})$")


class InvalidRunExport(ValueError):
    pass


@dataclass(frozen=True)
class DecodedRunExport:
    format: int
    run_id: str
    generated_at: datetime
    event_sequence: int
    event_hash: str
    current_kills: int
    checksum: str
    events: list[dict]

    @property
    def character_name(self):
        for event in self.events:
            if event["event_type"] != "session.started":
                continue
            character = event["payload"].get("character")
            if isinstance(character, dict):
                return str(
                    character.get("displayName")
                    or character.get("display_name")
                    or " ".join(
                        part
                        for part in (
                            str(character.get("forename") or "").strip(),
                            str(character.get("surname") or "").strip(),
                        )
                        if part
                    )
                ).strip()
        return ""

    @property
    def bootstrapped(self):
        return any(
            event["event_type"] == "day.started"
            and bool(event["payload"].get("partial"))
            for event in self.events
        )


def _read_frame(value, cursor, *, tagged=False):
    if cursor >= len(value):
        raise InvalidRunExport("The export contains a missing data frame.")
    tag = None
    if tagged:
        tag = chr(value[cursor])
        cursor += 1
    colon = value.find(b":", cursor)
    if colon < 0:
        raise InvalidRunExport("The export contains an invalid data frame.")
    length_text = value[cursor:colon]
    if not length_text.isdigit():
        raise InvalidRunExport("The export contains an invalid frame length.")
    length = int(length_text)
    first = colon + 1
    last = first + length
    if last > len(value):
        raise InvalidRunExport("The export contains a truncated data frame.")
    return tag, value[first:last], last


def _decompress(value):
    output = bytearray()
    cursor = 0
    while cursor < len(value):
        flags = value[cursor]
        cursor += 1
        for bit in range(8):
            if cursor >= len(value):
                break
            if flags & (1 << bit):
                output.append(value[cursor])
                cursor += 1
            else:
                if cursor + 1 >= len(value):
                    raise InvalidRunExport("The export compression stream is truncated.")
                high, low = value[cursor], value[cursor + 1]
                cursor += 2
                offset = high * 16 + low // 16
                match_length = low % 16 + 3
                if offset < 1 or offset > len(output):
                    raise InvalidRunExport("The export compression stream is invalid.")
                for _ in range(match_length):
                    output.append(output[-offset])
                    if len(output) > MAX_DECOMPRESSED_BYTES:
                        raise InvalidRunExport("The export is too large.")
            if len(output) > MAX_DECOMPRESSED_BYTES:
                raise InvalidRunExport("The export is too large.")
    return bytes(output)


def _decode_value(value, cursor=0):
    tag, content, next_cursor = _read_frame(value, cursor, tagged=True)
    if tag == "z":
        if content:
            raise InvalidRunExport("The export contains an invalid null value.")
        result = None
    elif tag == "b":
        if content not in {b"0", b"1"}:
            raise InvalidRunExport("The export contains an invalid boolean value.")
        result = content == b"1"
    elif tag == "n":
        text = content.decode("ascii")
        try:
            result = float(text) if any(marker in text for marker in ".eE") else int(text)
        except ValueError as exc:
            raise InvalidRunExport("The export contains an invalid number.") from exc
    elif tag == "s":
        result = content.decode("utf-8")
    elif tag == "a":
        result = []
        inner = 0
        while inner < len(content):
            item, inner = _decode_value(content, inner)
            result.append(item)
    elif tag == "m":
        result = {}
        inner = 0
        while inner < len(content):
            key_tag, key, inner = _read_frame(content, inner, tagged=True)
            if key_tag != "k":
                raise InvalidRunExport("The export contains an invalid map key.")
            item, inner = _decode_value(content, inner)
            result[key.decode("utf-8")] = item
    else:
        raise InvalidRunExport("The export contains an unsupported value type.")
    return result, next_cursor


def _decode_event(body):
    expected = ("v", "r", "e", "q", "t", "w", "y", "p")
    values = {}
    cursor = 0
    for expected_tag in expected:
        tag, content, cursor = _read_frame(body, cursor, tagged=True)
        if tag != expected_tag:
            raise InvalidRunExport("The export contains an invalid event record.")
        values[tag] = content
    if cursor != len(body) or values["v"] != b"1":
        raise InvalidRunExport("The export contains an unsupported event record.")
    payload, payload_cursor = _decode_value(values["p"])
    if payload_cursor != len(values["p"]) or not isinstance(payload, dict):
        raise InvalidRunExport("The export contains an invalid event payload.")
    try:
        return {
            "run_id": values["r"].decode("utf-8"),
            "epoch": int(values["e"]),
            "sequence": int(values["q"]),
            "utc": int(values["t"]),
            "world_age_hours": float(values["w"]),
            "event_type": values["y"].decode("utf-8"),
            "payload": payload,
        }
    except (UnicodeDecodeError, ValueError) as exc:
        raise InvalidRunExport("The export contains invalid event metadata.") from exc


def decode_run_export(value):
    value = "".join(str(value or "").split())
    if not value or len(value) > MAX_ENCODED_CHARACTERS:
        raise InvalidRunExport("Choose a valid Rat Race run export.")
    match = ENVELOPE_RE.fullmatch(value)
    if not match:
        raise InvalidRunExport("This is not a recognised Rat Race run export.")
    payload_text, checksum = match.groups()
    try:
        padding = "=" * ((4 - len(payload_text) % 4) % 4)
        compressed = base64.urlsafe_b64decode(payload_text + padding)
    except (ValueError, base64.binascii.Error) as exc:
        raise InvalidRunExport("The export uses invalid Base64URL data.") from exc
    canonical = _decompress(compressed)
    if hashlib.sha256(canonical).hexdigest() != checksum:
        raise InvalidRunExport("The export checksum does not match its contents.")

    fields = []
    cursor = 0
    _, format_field, cursor = _read_frame(canonical, cursor)
    try:
        export_format = int(format_field)
    except ValueError as exc:
        raise InvalidRunExport("The export format is invalid.") from exc
    if export_format != 2:
        raise InvalidRunExport("Please create a current format-2 Rat Race export.")
    fields.append(format_field)
    for _ in range(6):
        _, field, cursor = _read_frame(canonical, cursor)
        fields.append(field)
    if cursor != len(canonical):
        raise InvalidRunExport("The export contains unexpected trailing data.")
    try:
        run_id = fields[1].decode("utf-8")
        generated_utc = int(fields[2])
        event_count = int(fields[3])
        event_hash = fields[4].decode("ascii")
        current_kills = int(fields[5])
    except (UnicodeDecodeError, ValueError) as exc:
        raise InvalidRunExport("The export header is invalid.") from exc
    if not run_id or event_count < 0 or current_kills < 0:
        raise InvalidRunExport("The export header contains invalid values.")
    if not re.fullmatch(r"[0-9a-f]{64}", event_hash):
        raise InvalidRunExport("The export ledger head is invalid.")

    bodies = []
    body_cursor = 0
    for _ in range(event_count):
        _, body, body_cursor = _read_frame(fields[6], body_cursor)
        bodies.append(body)
    if body_cursor != len(fields[6]):
        raise InvalidRunExport("The export event count does not match its contents.")

    events = []
    previous_hash = GENESIS_HASH
    for sequence, body in enumerate(bodies, start=1):
        event = _decode_event(body)
        if event["run_id"] != run_id or event["sequence"] != sequence:
            raise InvalidRunExport("The export event sequence is invalid.")
        previous_hash = hashlib.sha256(previous_hash.encode("ascii") + body).hexdigest()
        events.append(event)
    if previous_hash != event_hash:
        raise InvalidRunExport("The export ledger hash does not match its events.")
    try:
        generated_at = datetime.fromtimestamp(generated_utc, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise InvalidRunExport("The export timestamp is invalid.") from exc
    return DecodedRunExport(
        format=export_format,
        run_id=run_id,
        generated_at=generated_at,
        event_sequence=event_count,
        event_hash=event_hash,
        current_kills=current_kills,
        checksum=checksum,
        events=events,
    )

import base64
import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone


PREFIX = "TGSRR1.LZ1."
BLOCK_PREFIX = "TGSRR1.BLK1."
GENESIS_HASH = "0" * 64
SUPPORTED_EVENT_SCHEMAS = {2}
MAX_DECOMPRESSED_BYTES = 16 * 1024 * 1024
MAX_ENCODED_CHARACTERS = 24 * 1024 * 1024 + len(PREFIX) + 65
MAX_RUN_ID_CHARACTERS = 160
MAX_DATABASE_INTEGER = 2**63 - 1
SUPPORTED_PROJECTION_SCHEMAS = {1, 2}
OUTPOST_IDS = {
    "brandenburg", "echo_creek", "ekron", "fallas_lake",
    "hog_wallow_military_base", "irvington", "louisville", "march_ridge",
    "muldraugh", "riverside", "rosewood", "valley_station", "west_point",
}
OUTPOST_DELIVERABLE_IDS = {
    "room_activation", "floor_activation", "zombie_clearance",
    "window_barricades", "enclosed", "doors_fitted", "doors_closed",
    "good_bed", "generator", "food", "plumbed_sink", "spare_car",
    "engine_start",
}
ENVELOPE_RE = re.compile(r"^TGSRR1\.LZ1\.([A-Za-z0-9_-]+)\.([0-9a-f]{64})$")
CANONICAL_NUMBER_RE = re.compile(
    rb"^(?:0|-?(?:[1-9]\d*(?:\.\d+)?(?:e[+-]?\d+)?|0\.\d+))$"
)


class InvalidRunExport(ValueError):
    pass


def _valid_lifecycle_point(point, *, require_sequence=False):
    if not isinstance(point, dict):
        return False
    integer_fields = ("utc",)
    number_fields = ("worldAgeHours", "elapsedDays")
    return (
        (not require_sequence or (
            not isinstance(point.get("sequence"), bool)
            and isinstance(point.get("sequence"), int)
            and point["sequence"] >= 1
        ))
        and ("sequence" not in point or (
            not isinstance(point["sequence"], bool)
            and isinstance(point["sequence"], int)
            and point["sequence"] >= 1
        ))
        and all(
            not isinstance(point.get(field), bool)
            and isinstance(point.get(field), int)
            and point[field] >= 0
            for field in integer_fields
        )
        and all(
            not isinstance(point.get(field), bool)
            and isinstance(point.get(field), (int, float))
            and math.isfinite(point[field])
            and point[field] >= 0
            for field in number_fields
        )
    )


def _validate_lifecycle_summary(summary, current_complete):
    if not isinstance(summary, dict):
        return False
    completion_count = summary.get("completionCount")
    regression_count = summary.get("regressionCount")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in (completion_count, regression_count)
    ):
        return False
    if summary.get("currentState") != (
        "complete" if current_complete else "incomplete"
    ):
        return False
    first = summary.get("firstCompletion")
    latest = summary.get("latestCompletion")
    regression = summary.get("latestRegression")
    if completion_count == 0:
        if first is not None or latest is not None:
            return False
    elif not _valid_lifecycle_point(first, require_sequence=True) or not _valid_lifecycle_point(latest):
        return False
    if regression_count == 0:
        if regression is not None:
            return False
    elif not _valid_lifecycle_point(regression):
        return False
    return True


def _validate_outpost_lifecycles(projection):
    outposts = projection.get("outposts")
    if not isinstance(outposts, list) or len(outposts) > len(OUTPOST_IDS):
        return False
    observed_outposts = set()
    for outpost in outposts:
        if not isinstance(outpost, dict) or outpost.get("id") not in OUTPOST_IDS:
            return False
        outpost_id = outpost["id"]
        if outpost_id in observed_outposts:
            return False
        observed_outposts.add(outpost_id)
        if not isinstance(outpost.get("complete"), bool) or not _validate_lifecycle_summary(
            outpost.get("lifecycle"), outpost["complete"]
        ):
            return False
        deliverables = outpost.get("deliverables")
        if not isinstance(deliverables, list) or len(deliverables) > len(OUTPOST_DELIVERABLE_IDS):
            return False
        observed_deliverables = set()
        deliverables_by_id = {}
        for deliverable in deliverables:
            if (
                not isinstance(deliverable, dict)
                or deliverable.get("id") not in OUTPOST_DELIVERABLE_IDS
                or deliverable["id"] in observed_deliverables
                or not isinstance(deliverable.get("passed"), bool)
                or not _validate_lifecycle_summary(
                    deliverable.get("lifecycle"), deliverable["passed"]
                )
            ):
                return False
            observed_deliverables.add(deliverable["id"])
            deliverables_by_id[deliverable["id"]] = deliverable
        engine_start = deliverables_by_id.get("engine_start")
        spare_car = deliverables_by_id.get("spare_car")
        if (
            engine_start
            and engine_start["passed"]
            and (not spare_car or not spare_car["passed"])
        ):
            return False
    return True


def _validate_outpost_lifecycle_history(projection, events):
    outposts = {outpost["id"]: outpost for outpost in projection["outposts"]}
    grouped = {}
    relevant_types = {"outpost.completed", "outpost.deliverable.completed"}
    forbidden_types = {"outpost.regressed", "outpost.deliverable.regressed"}
    for event in events:
        if event["event_type"] in forbidden_types:
            return False
        if event["event_type"] not in relevant_types:
            continue
        payload = event["payload"]
        outpost_id = payload.get("outpostId")
        deliverable_id = payload.get("deliverableId")
        if outpost_id not in outposts:
            return False
        if deliverable_id is not None and deliverable_id not in OUTPOST_DELIVERABLE_IDS:
            return False
        if deliverable_id is not None and deliverable_id not in {
            deliverable["id"] for deliverable in outposts[outpost_id]["deliverables"]
        }:
            return False
        grouped.setdefault((outpost_id, deliverable_id), []).append(event)

    for outpost_id, outpost in outposts.items():
        subjects = [(None, outpost)] + [
            (deliverable["id"], deliverable)
            for deliverable in outpost["deliverables"]
        ]
        for deliverable_id, subject in subjects:
            summary = subject["lifecycle"]
            subject_events = grouped.get((outpost_id, deliverable_id), [])
            completions = [
                event for event in subject_events
                if event["event_type"].endswith("completed")
            ]
            if len(completions) != (1 if summary["completionCount"] > 0 else 0):
                return False
            point = summary.get("firstCompletion")
            event = completions[0] if completions else None
            if not (point is None and event is None) and (
                point is None or event is None or any(
                    point[key] != event[event_key]
                    for key, event_key in (
                        ("sequence", "sequence"),
                        ("utc", "utc"),
                        ("worldAgeHours", "world_age_hours"),
                    )
                )
            ):
                return False
    return True


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
    projection: dict
    event_blocks: tuple[dict, ...] = ()

    @property
    def lifecycle(self):
        return self.projection.get("lifecycle") or "active"

    @property
    def character_name(self):
        character_projection = self.projection.get("character")
        if isinstance(character_projection, dict):
            for snapshot_name in ("current", "starting"):
                snapshot = character_projection.get(snapshot_name)
                if not isinstance(snapshot, dict):
                    continue
                display_name = str(
                    snapshot.get("displayName")
                    or snapshot.get("display_name")
                    or " ".join(
                        part
                        for part in (
                            str(snapshot.get("forename") or "").strip(),
                            str(snapshot.get("surname") or "").strip(),
                        )
                        if part
                    )
                ).strip()
                if display_name:
                    return display_name
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

    @property
    def challenge_id(self):
        challenge = self.projection.get("challenge")
        return challenge.get("id", "") if isinstance(challenge, dict) else ""

    @property
    def challenge_game_mode(self):
        challenge = self.projection.get("challenge")
        return challenge.get("gameMode", "") if isinstance(challenge, dict) else ""


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
        if not CANONICAL_NUMBER_RE.fullmatch(content):
            raise InvalidRunExport("The export contains an invalid number.")
        try:
            text = content.decode("ascii")
            result = float(text) if any(marker in text for marker in ".e") else int(text)
        except (OverflowError, UnicodeDecodeError, ValueError) as exc:
            raise InvalidRunExport("The export contains an invalid number.") from exc
        if isinstance(result, float) and not math.isfinite(result):
            raise InvalidRunExport("The export contains an invalid number.")
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
            if key_tag != "k" or not key:
                raise InvalidRunExport("The export contains an invalid map key.")
            item, inner = _decode_value(content, inner)
            try:
                decoded_key = key.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise InvalidRunExport("The export contains an invalid map key.") from exc
            if decoded_key in result:
                raise InvalidRunExport("The export contains a duplicate map key.")
            result[decoded_key] = item
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
    try:
        event_schema = int(values["v"])
    except ValueError as exc:
        raise InvalidRunExport("The export contains an unsupported event record.") from exc
    if cursor != len(body) or event_schema not in SUPPORTED_EVENT_SCHEMAS:
        raise InvalidRunExport("The export contains an unsupported event record.")
    payload, payload_cursor = _decode_value(values["p"])
    if payload_cursor != len(values["p"]) or not isinstance(payload, dict):
        raise InvalidRunExport("The export contains an invalid event payload.")
    try:
        event = {
            "schema": event_schema,
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
    if (
        not event["run_id"]
        or event["epoch"] < 1
        or event["sequence"] < 1
        or event["utc"] < 0
        or not math.isfinite(event["world_age_hours"])
        or not event["event_type"]
    ):
        raise InvalidRunExport("The export contains invalid event metadata.")
    return event


def decode_run_export(value, *, block_cache=None):
    value = "".join(str(value or "").split())
    if not value or len(value) > MAX_ENCODED_CHARACTERS:
        raise InvalidRunExport("Choose a valid Rat Race run export.")
    match = ENVELOPE_RE.fullmatch(value)
    event_blocks = None
    bodies = []
    cached_events = []
    decoded_blocks = []
    if match:
        payload_text, checksum = match.groups()
    elif value.startswith(BLOCK_PREFIX):
        parts = value.split(".")
        if (
            len(parts) < 4
            or len(parts) % 2
            or parts[:2] != ["TGSRR1", "BLK1"]
            or any(not re.fullmatch(r"[A-Za-z0-9_-]+", part) for part in parts[2::2])
            or any(not re.fullmatch(r"[0-9a-f]{64}", part) for part in parts[3::2])
        ):
            raise InvalidRunExport("This is not a recognised Rat Race run export.")
        payload_text, checksum = parts[2:4]
    else:
        raise InvalidRunExport("This is not a recognised Rat Race run export.")
    try:
        padding = "=" * ((4 - len(payload_text) % 4) % 4)
        compressed = base64.urlsafe_b64decode(payload_text + padding)
    except (ValueError, base64.binascii.Error) as exc:
        raise InvalidRunExport("The export uses invalid Base64URL data.") from exc
    canonical = _decompress(compressed)
    if hashlib.sha256(canonical).hexdigest() != checksum:
        raise InvalidRunExport("The export checksum does not match its contents.")

    if match:
        fields = []
        cursor = 0
        _, format_field, cursor = _read_frame(canonical, cursor)
        try:
            export_format = int(format_field)
        except ValueError as exc:
            raise InvalidRunExport("The export format is invalid.") from exc
        if export_format != 3:
            raise InvalidRunExport("Please create a current Rat Race export.")
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
        except (UnicodeDecodeError, ValueError) as exc:
            raise InvalidRunExport("The export header is invalid.") from exc
        projection, projection_cursor = _decode_value(fields[5])
        if projection_cursor != len(fields[5]):
            raise InvalidRunExport("The export projection contains trailing data.")
        body_cursor = 0
        for _ in range(event_count):
            _, body, body_cursor = _read_frame(fields[6], body_cursor)
            bodies.append(body)
        if body_cursor != len(fields[6]):
            raise InvalidRunExport("The export event count does not match its contents.")
    else:
        manifest, manifest_cursor = _decode_value(canonical)
        if manifest_cursor != len(canonical) or not isinstance(manifest, dict):
            raise InvalidRunExport("The export contains an invalid block manifest.")
        try:
            export_format = manifest["format"]
            run_id = manifest["runId"]
            generated_utc = manifest["generatedUtc"]
            event_count = manifest["eventSequence"]
            event_hash = manifest["eventHash"]
            projection = manifest["projection"]
            event_blocks = manifest["eventBlocks"]
        except KeyError as exc:
            raise InvalidRunExport("The export block manifest is incomplete.") from exc
        if export_format != 4 or not isinstance(event_blocks, list):
            raise InvalidRunExport("Please create a current Rat Race export.")
        if len(parts) != 4 + len(event_blocks) * 2:
            raise InvalidRunExport("The export block count does not match its manifest.")
        if block_cache:
            block_cache.prepare(event_blocks)
        expected_first = 1
        for index, descriptor in enumerate(event_blocks):
            if not isinstance(descriptor, dict):
                raise InvalidRunExport("The export contains an invalid event block.")
            count = descriptor.get("count")
            first = descriptor.get("firstSequence")
            last = descriptor.get("lastSequence")
            block_checksum = parts[5 + index * 2]
            if (
                isinstance(count, bool)
                or not isinstance(count, int)
                or count < 1
                or first != expected_first
                or last != first + count - 1
                or descriptor.get("checksum") != block_checksum
                or not re.fullmatch(r"[0-9a-f]{64}", str(descriptor.get("lastHash", "")))
            ):
                raise InvalidRunExport("The export contains an invalid event block descriptor.")
            block_payload = parts[4 + index * 2]
            cached = block_cache.get(descriptor) if block_cache else None
            if cached:
                block_canonical = cached["canonical"]
                block_events = cached["events"]
                if not isinstance(block_canonical, bytes) or not isinstance(block_events, list):
                    raise InvalidRunExport("A cached export block is invalid.")
            else:
                padding = "=" * ((4 - len(block_payload) % 4) % 4)
                try:
                    compressed_block = base64.urlsafe_b64decode(block_payload + padding)
                except (ValueError, base64.binascii.Error) as exc:
                    raise InvalidRunExport("An export block uses invalid Base64URL data.") from exc
                block_canonical = _decompress(compressed_block)
                if hashlib.sha256(block_canonical).hexdigest() != block_checksum:
                    raise InvalidRunExport("An export block checksum does not match its contents.")
                block_events = []
            block_cursor = 0
            block_bodies = []
            for _ in range(count):
                _, body, block_cursor = _read_frame(block_canonical, block_cursor)
                block_bodies.append(body)
            if block_cursor != len(block_canonical):
                raise InvalidRunExport("An export block contains unexpected trailing data.")
            if block_events and len(block_events) != count:
                raise InvalidRunExport("A cached export block has an invalid event count.")
            bodies.extend(block_bodies)
            cached_events.extend(block_events or ([None] * count))
            decoded_blocks.append({
                "position": index,
                "descriptor": descriptor,
                "canonical": block_canonical,
            })
            expected_first = last + 1
        if expected_first - 1 != event_count:
            raise InvalidRunExport("The export event count does not match its blocks.")
    if (
        not run_id
        or len(run_id) > MAX_RUN_ID_CHARACTERS
        or generated_utc < 0
        or event_count < 0
        or event_count > MAX_DATABASE_INTEGER
    ):
        raise InvalidRunExport("The export header contains invalid values.")
    if not re.fullmatch(r"[0-9a-f]{64}", event_hash):
        raise InvalidRunExport("The export ledger head is invalid.")

    if not isinstance(projection, dict):
        raise InvalidRunExport("The export contains an invalid run projection.")
    current_kills = projection.get("currentKills")
    if (
        projection.get("schema") not in SUPPORTED_PROJECTION_SCHEMAS
        or isinstance(current_kills, bool)
        or not isinstance(current_kills, int)
        or current_kills < 0
        or current_kills > MAX_DATABASE_INTEGER
        or not isinstance(projection.get("character"), dict)
    ):
        raise InvalidRunExport("The export contains an unsupported run projection.")
    challenge = projection.get("challenge")
    if challenge is not None and (
        not isinstance(challenge, dict)
        or not isinstance(challenge.get("id"), str)
        or len(challenge["id"]) > 160
        or not isinstance(challenge.get("gameMode"), str)
        or not challenge["gameMode"]
        or len(challenge["gameMode"]) > 255
    ):
        raise InvalidRunExport("The export contains invalid challenge evidence.")
    starting_location = projection["character"].get("startingLocation")
    registered_location = (
        starting_location.get("registeredLocation")
        if isinstance(starting_location, dict)
        else None
    )
    if starting_location is not None and (
        not isinstance(starting_location, dict)
        or any(
            isinstance(starting_location.get(key), bool)
            or not isinstance(starting_location.get(key), int)
            for key in ("x", "y", "z", "capturedUtc")
        )
        or starting_location["capturedUtc"] < 0
        or isinstance(starting_location.get("worldAgeHours"), bool)
        or not isinstance(starting_location.get("worldAgeHours"), (int, float))
        or not math.isfinite(starting_location["worldAgeHours"])
        or starting_location["worldAgeHours"] < 0
        or not isinstance(starting_location.get("buildingId"), str)
        or len(starting_location["buildingId"]) > 160
        or ("partial" in starting_location
            and not isinstance(starting_location.get("partial"), bool))
        or (
            registered_location is not None
            and (
                not isinstance(registered_location, dict)
                or registered_location.get("kind") not in {"outpost", "landmark"}
                or not isinstance(registered_location.get("id"), str)
                or not registered_location["id"]
                or len(registered_location["id"]) > 255
                or isinstance(registered_location.get("registryVersion"), bool)
                or not isinstance(registered_location.get("registryVersion"), int)
                or registered_location["registryVersion"] < 1
            )
        )
    ):
        raise InvalidRunExport("The export contains invalid starting-location evidence.")
    chosen_starting_region = projection["character"].get("chosenStartingRegion")
    if chosen_starting_region is not None and (
        not isinstance(chosen_starting_region, dict)
        or chosen_starting_region.get("schema") != 1
        or chosen_starting_region.get("selectionMode") not in {"explicit", "random"}
        or not isinstance(chosen_starting_region.get("resolvedRegionId"), str)
        or not chosen_starting_region["resolvedRegionId"]
        or len(chosen_starting_region["resolvedRegionId"]) > 255
        or isinstance(chosen_starting_region.get("capturedUtc"), bool)
        or not isinstance(chosen_starting_region.get("capturedUtc"), int)
        or chosen_starting_region["capturedUtc"] < 0
    ):
        raise InvalidRunExport("The export contains invalid chosen-region evidence.")
    if projection["schema"] >= 2 and not _validate_outpost_lifecycles(projection):
        raise InvalidRunExport("The export contains invalid outpost lifecycle summaries.")

    events = []
    previous_hash = GENESIS_HASH
    for sequence, body in enumerate(bodies, start=1):
        event = cached_events[sequence - 1] if cached_events else None
        if event is None:
            event = _decode_event(body)
        if event["run_id"] != run_id or event["sequence"] != sequence:
            raise InvalidRunExport("The export event sequence is invalid.")
        previous_hash = hashlib.sha256(previous_hash.encode("ascii") + body).hexdigest()
        if event_blocks:
            descriptor = next(
                (item for item in event_blocks if item["lastSequence"] == sequence),
                None,
            )
            if descriptor and descriptor["lastHash"] != previous_hash:
                raise InvalidRunExport("An export block ledger head is invalid.")
        events.append(event)
    if previous_hash != event_hash:
        raise InvalidRunExport("The export ledger hash does not match its events.")
    if projection["schema"] >= 2 and not _validate_outpost_lifecycle_history(
        projection, events
    ):
        raise InvalidRunExport(
            "The outpost lifecycle summaries do not match the verified ledger."
        )

    lifecycle = projection.get("lifecycle")
    terminal_events = [event for event in events if event["event_type"] == "run.ended"]
    if len(terminal_events) > 1:
        raise InvalidRunExport("The export contains duplicate terminal run events.")
    if lifecycle is not None and lifecycle not in {"active", "deceased"}:
        raise InvalidRunExport("The export contains an unsupported run lifecycle.")
    if lifecycle == "deceased":
        ended_reason = projection.get("endedReason")
        ended_utc = projection.get("endedUtc")
        ended_world_age = projection.get("endedWorldAgeHours")
        ended_sequence = projection.get("endedEventSequence")
        if (
            ended_reason != "deceased"
            or isinstance(ended_utc, bool)
            or not isinstance(ended_utc, int)
            or ended_utc < 0
            or isinstance(ended_world_age, bool)
            or not isinstance(ended_world_age, (int, float))
            or not math.isfinite(ended_world_age)
            or ended_world_age < 0
            or isinstance(ended_sequence, bool)
            or not isinstance(ended_sequence, int)
            or ended_sequence < 1
            or len(terminal_events) != 1
        ):
            raise InvalidRunExport("The deceased run has incomplete terminal evidence.")
        terminal_event = terminal_events[0]
        if (
            terminal_event["payload"].get("reason") != "deceased"
            or terminal_event["sequence"] != ended_sequence
            or terminal_event["utc"] != ended_utc
            or terminal_event["world_age_hours"] != ended_world_age
        ):
            raise InvalidRunExport("The terminal run evidence does not match its projection.")
    elif terminal_events:
        raise InvalidRunExport("The terminal run event has no matching lifecycle projection.")
    elif any(
        key in projection
        for key in (
            "endedReason",
            "endedUtc",
            "endedWorldAgeHours",
            "endedEventSequence",
        )
    ):
        raise InvalidRunExport("The active run contains terminal projection fields.")
    try:
        generated_at = datetime.fromtimestamp(generated_utc, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise InvalidRunExport("The export timestamp is invalid.") from exc
    for block in decoded_blocks:
        descriptor = block["descriptor"]
        first = descriptor["firstSequence"]
        block["starting_hash"] = (
            GENESIS_HASH if first == 1 else next(
                item["lastHash"]
                for item in event_blocks
                if item["lastSequence"] == first - 1
            )
        )
        block["events"] = events[first - 1:descriptor["lastSequence"]]

    return DecodedRunExport(
        format=export_format,
        run_id=run_id,
        generated_at=generated_at,
        event_sequence=event_count,
        event_hash=event_hash,
        current_kills=current_kills,
        checksum=checksum,
        events=events,
        projection=projection,
        event_blocks=tuple(decoded_blocks),
    )

import hashlib
import io
import json
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree


SHEET_ID = "1qQWLEajgU58FXO83_Xn85rZ8jm6BhUv5VdpIraNfBUQ"
SOURCE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"
WORKSHEET = "Historical Leaderboard"
DEFAULT_SNAPSHOT = Path(__file__).resolve().parent / "data" / "legacy_hall_of_fame.json"
NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}


def _decimal(value, label):
    try:
        result = Decimal(str(value or 0))
    except InvalidOperation as exc:
        raise ValueError(f"{label} is not numeric.") from exc
    if result < 0:
        raise ValueError(f"{label} cannot be negative.")
    return result


def _column_number(reference):
    letters = re.match(r"[A-Z]+", reference).group(0)
    result = 0
    for letter in letters:
        result = result * 26 + ord(letter) - 64
    return result


def _sheet_rows(workbook_bytes):
    with zipfile.ZipFile(io.BytesIO(workbook_bytes)) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root.findall("x:si", NS)]
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheet = next(
            (item for item in workbook.findall("x:sheets/x:sheet", NS) if item.attrib["name"] == WORKSHEET),
            None,
        )
        if sheet is None:
            raise ValueError(f"Worksheet {WORKSHEET!r} was not found.")
        relationship_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        target = next(item.attrib["Target"] for item in relationships.findall("r:Relationship", REL_NS) if item.attrib["Id"] == relationship_id)
        path = "xl/" + target.lstrip("/")
        root = ElementTree.fromstring(archive.read(path))
        for row in root.findall("x:sheetData/x:row", NS):
            values = {}
            for cell in row.findall("x:c", NS):
                column = _column_number(cell.attrib["r"])
                value = cell.find("x:v", NS)
                text = "" if value is None else value.text or ""
                if cell.attrib.get("t") == "s" and text:
                    text = shared[int(text)]
                elif cell.attrib.get("t") == "inlineStr":
                    inline = cell.find("x:is", NS)
                    text = "" if inline is None else "".join(inline.itertext())
                values[column] = text
            yield int(row.attrib["r"]), values


def build_snapshot(workbook_bytes, captured_at=None):
    captured_at = captured_at or datetime.now(timezone.utc)
    entries = []
    source_keys = set()
    for source_row, row in _sheet_rows(workbook_bytes):
        rank_text = str(row.get(1, "")).strip()
        if source_row < 5 or not rank_text:
            continue
        try:
            rank = int(Decimal(rank_text))
        except (InvalidOperation, ValueError):
            rank = len(entries) + 1
        name = str(row.get(2, "")).strip()
        normalized_name = " ".join(name.casefold().split())
        if not normalized_name:
            raise ValueError(f"Row {source_row} has a blank participant name.")
        signature = "|".join(
            str(row.get(column, "")).strip() for column in (2, 3, 4, 5, 8, 9, 10, 11)
        ).casefold()
        source_key = hashlib.sha256(signature.encode("utf-8")).hexdigest()
        if source_key in source_keys:
            source_key = hashlib.sha256(f"{signature}|row:{source_row}".encode("utf-8")).hexdigest()
        source_keys.add(source_key)
        entries.append({
            "source_key": source_key,
            "source_row": source_row,
            "source_rank": rank,
            "historical_name": name,
            "zombie_kills": int(_decimal(row.get(3), "Zombie kills")),
            "survival_time_full": str(row.get(4, "")).strip(),
            "survival_days": str(_decimal(row.get(5), "Survival days")),
            "kills_per_day": str(_decimal(row.get(6), "Kills per day")),
            "playtime_hours": str(_decimal(row.get(7), "Playtime")),
            "outposts_cleared": int(_decimal(row.get(8), "Outposts")),
            "maxed_skills": int(_decimal(row.get(9), "Maxed skills")),
            "challenge_progress": str(_decimal(row.get(10), "Challenge progress")),
            "source_url": str(row.get(11, "")).strip(),
        })
    if not entries:
        raise ValueError("The historical worksheet did not contain any ranked entries.")
    snapshot_id = f"legacy-hall-of-fame-{captured_at.date().isoformat()}"
    return {
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "captured_at": captured_at.isoformat(),
        "source_url": SOURCE_URL,
        "worksheet": WORKSHEET,
        "entry_count": len(entries),
        "entries": entries,
    }


def download_workbook():
    request = urllib.request.Request(EXPORT_URL, headers={"User-Agent": "TGSRR-Legacy-Snapshot/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def write_snapshot(snapshot, path=DEFAULT_SNAPSHOT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path

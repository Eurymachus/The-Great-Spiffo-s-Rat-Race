"""Build isolated synthetic leaderboard snapshots for the Workshop upload probe."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "daily-leaderboard-workshop-probe"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("revision", type=int, choices=(1, 2))
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    vdf = OUT / "upload.vdf"
    item_id = "0"
    if vdf.exists():
        match = re.search(r'"publishedfileid"\s+"(\d+)"', vdf.read_text())
        if not match:
            raise SystemExit("Existing VDF has no item ID; reconcile before proceeding.")
        item_id = match[1]
    if args.revision == 2 and item_id == "0":
        raise SystemExit("Revision 2 requires an existing Workshop item.")
    if args.revision == 1 and item_id != "0":
        raise SystemExit("Item already exists; do not recreate revision 1.")
    mod = OUT / "Contents" / "mods" / "TGSRRDailyLeaderboardProbe"
    (mod / "common").mkdir(parents=True, exist_ok=True)
    version = mod / "42"
    lua = version / "media" / "lua" / "client"
    lua.mkdir(parents=True, exist_ok=True)
    (version / "mod.info").write_text(
        "name=TGSRR Daily Leaderboard - Upload Test\n"
        "id=TGSRRDailyLeaderboardProbe\n"
        "author=Eurymachus\n"
        "description=Unlisted upload automation test. Synthetic standings only.\n"
        f"modversion=0.0.{args.revision}\nversionMin=42.0\n", encoding="utf-8")
    score = args.revision * 100
    (lua / "TGSRRDailyLeaderboardProbe.lua").write_text(
        "-- Synthetic data for the automated Workshop upload test.\n"
        "TGSRRDailyLeaderboardProbe = {\n"
        f"    revision = {args.revision},\n"
        "    synthetic = true,\n"
        f'    standings = {{ {{ name = "Test Racer", score = {score} }} }},\n'
        "}\n"
        f'print("[TGSRR Daily Leaderboard Probe] revision {args.revision}, synthetic score {score}")\n',
        encoding="utf-8")
    shutil.copyfile(ROOT / "preview.png", OUT / "preview.png")
    fields = {
        "appid": "108600", "publishedfileid": item_id,
        "contentfolder": (OUT / "Contents").as_posix(),
        "previewfile": (OUT / "preview.png").as_posix(),
        "visibility": "3",
        "title": "TGSRR Daily Leaderboard - Upload Test",
        "description": "Unlisted test of automated Workshop uploads for The Great Spiffo's Rat Race. Contains synthetic leaderboard data only, not real standings. Not affiliated with The Indie Stone.",
        "changenote": f"Automated upload test: snapshot {args.revision}, synthetic score {score}.",
    }
    vdf.write_text('"workshopitem"\n{\n' + ''.join(
        f'    "{key}" "{value}"\n' for key, value in fields.items()) + '}\n', encoding="utf-8")
    manifest = {p.relative_to(OUT / "Contents").as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted((OUT / "Contents").rglob("*")) if p.is_file()}
    (OUT / f"snapshot-{args.revision}-sha256.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"revision": args.revision, "item_id": item_id, "visibility": "Unlisted", "files": manifest, "vdf": str(vdf)}, indent=2))


if __name__ == "__main__":
    main()

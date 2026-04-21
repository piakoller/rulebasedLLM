import argparse
import json
from pathlib import Path


def strip_framing(in_path: Path, out_path: Path):
    data = json.loads(in_path.read_text(encoding="utf-8"))
    rows = data.get("rows", [])
    for row in rows:
        ar = row.get("agent_response")
        if isinstance(ar, dict):
            ar.pop("active_frame", None)
            ar.pop("next_frame", None)
            ar.pop("filled_slots", None)
    data["rows"] = rows
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="Strip dialogue framing fields from results JSON")
    p.add_argument("input", help="Input results JSON file")
    p.add_argument("--out", help="Output file path (optional)")
    args = p.parse_args()
    in_path = Path(args.input)
    if not in_path.exists():
        raise SystemExit(f"Input file not found: {in_path}")
    out_path = Path(args.out) if args.out else in_path.with_name(in_path.stem + "_noframe" + in_path.suffix)
    strip_framing(in_path, out_path)
    print(f"Wrote cleaned file: {out_path}")


if __name__ == "__main__":
    main()

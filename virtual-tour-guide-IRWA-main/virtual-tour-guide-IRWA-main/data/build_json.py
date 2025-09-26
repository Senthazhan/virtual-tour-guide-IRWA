import csv, json, os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
json_path = ROOT / "data" / "places.json"
csv_path = ROOT / "data" / "sri_lanka_places.csv"

# Load existing JSON (tolerate BOM)
data = {}
if json_path.exists():
    txt = json_path.read_text(encoding="utf-8-sig")
    try:
        data = json.loads(txt)
    except Exception as e:
        raise SystemExit(f"Failed to parse {json_path}: {e}")

def row_to_entry(r):
    def as_int(x, default=0):
        try: return int(str(x).strip())
        except: return default
    stops = []
    if r.get("stop1"):
        stops.append({"name": r["stop1"].strip(), "minutes": as_int(r.get("stop1_minutes"), 45)})
    if r.get("stop2"):
        stops.append({"name": r["stop2"].strip(), "minutes": as_int(r.get("stop2_minutes"), 45)})
    if r.get("stop3"):
        stops.append({"name": r["stop3"].strip(), "minutes": as_int(r.get("stop3_minutes"), 45)})
    facts = [r.get("fact1","").strip(), r.get("fact2","").strip(), r.get("fact3","").strip()]
    facts = [f for f in facts if f]
    return {
        "facts": facts[:3],
        "ticket": (r.get("ticket") or "Ticket info varies by site.").strip(),
        "stops": stops
    }

# Merge CSV rows
with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)
    for r in reader:
        place = (r.get("place") or "").strip()
        if not place: 
            continue
        data[place] = row_to_entry(r)

# Save pretty JSON (no BOM)
json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Wrote {json_path} with {len(data)} places")

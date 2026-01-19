#!/usr/bin/env python3
"""
Geocode Berlin bridges from Wikipedia bridge list (A-Z subpages).

Reads bruecken_tagesspiegel.json and fills in lat/lon from Wikipedia.
Outputs bruecken_geocoded.json and unmatched.csv for manual review.

Usage:
    pip install requests beautifulsoup4 lxml
    python geocode_bridges.py
"""

import json
import re
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

WIKI_BASE = "https://de.wikipedia.org/wiki/Liste_der_Br%C3%BCcken_in_Berlin"
# Wikipedia uses bundled subpages (not every single letter)
WIKI_SEGMENTS = ["A", "B", "CD", "E", "F", "G", "H", "IJ", "K", "L", "M", "N", "O", "PQ", "R", "S", "T", "UV", "W", "XYZ"]

UA = {"User-Agent": "BridgeSafetyCoordBot/1.0 (Berlin bridge data project)"}

COORD_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)")


def strip_footnotes(s: str) -> str:
    """Remove [1], [12] etc. footnote markers."""
    return re.sub(r"\[\s*\d+\s*\]", "", s)


def normalize_name(s: str) -> str:
    """Normalize bridge name for matching."""
    s = strip_footnotes(s)
    s = s.replace("–", "-").replace("—", "-")
    s = s.replace("ß", "ss")

    # Normalize umlauts
    repl = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"}
    for k, v in repl.items():
        s = s.replace(k, v)

    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)

    # Remove diacritical marks
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))

    # Remove non-alphanumeric except spaces and hyphens
    s = re.sub(r"[^a-z0-9 \-]", "", s)
    s = s.strip()
    return s


def fetch_wiki_segment(segment: str) -> str:
    """Fetch HTML content of a Wikipedia bridge list subpage."""
    url = f"{WIKI_BASE}/{segment}"
    print(f"  Fetching {url}...")
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    return r.text


def build_wiki_index() -> dict:
    """
    Build index: normalized_bridge_name -> dict(lat, lon, source_url, raw_name)
    """
    print("Building Wikipedia bridge index...")
    index = {}

    for seg in WIKI_SEGMENTS:
        try:
            html = fetch_wiki_segment(seg)
        except Exception as e:
            print(f"  Warning: Failed to fetch segment {seg}: {e}")
            continue

        soup = BeautifulSoup(html, "lxml")

        # Usually the first wikitable is the bridge list
        tables = soup.select("table.wikitable")
        if not tables:
            continue

        for table in tables:
            for row in table.select("tr"):
                cells = row.select("td")
                if len(cells) < 5:
                    continue

                # Columns: Photo | Name | Ortsteil | Notes | Location
                name_text = cells[1].get_text(" ", strip=True)
                lage_text = cells[4].get_text(" ", strip=True)

                m = COORD_RE.search(lage_text)
                if not m:
                    continue

                lat = float(m.group(1))
                lon = float(m.group(2))

                key = normalize_name(name_text)
                index[key] = {
                    "lat": lat,
                    "lon": lon,
                    "source_url": f"{WIKI_BASE}/{seg}",
                    "raw_name": name_text,
                }

    print(f"  Found {len(index)} bridges with coordinates")
    return index


def main():
    input_file = Path("bruecken_tagesspiegel.json")

    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return

    print(f"Reading {input_file}...")
    data = json.loads(input_file.read_text(encoding="utf-8"))

    wiki_index = build_wiki_index()

    unmatched = []
    matched_count = 0
    already_have_coords = 0

    print("\nMatching bridges...")
    for b in data["bruecken"]:
        if b.get("lat") is not None and b.get("lon") is not None:
            already_have_coords += 1
            continue

        # Match primarily via b["name"], fallback via b["original"] if present
        candidates = [b.get("name", "")]
        if b.get("original"):
            candidates.append(b["original"])

        hit = None
        for cand in candidates:
            key = normalize_name(cand)
            if key in wiki_index:
                hit = wiki_index[key]
                break

        if hit:
            b["lat"] = hit["lat"]
            b["lon"] = hit["lon"]
            b["coord_quelle"] = f'Wikipedia: {hit["raw_name"]} ({hit["source_url"]})'
            matched_count += 1
        else:
            unmatched.append({
                "id": b["id"],
                "bezirk": b["bezirk"],
                "name": b.get("name"),
                "detail": b.get("detail"),
            })

    # Write output
    output_file = Path("bruecken_geocoded.json")
    output_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\nOutput: {output_file}")

    # Write unmatched report
    if unmatched:
        csv_file = Path("unmatched_bridges.csv")
        lines = ["id,bezirk,name,detail"]
        for u in unmatched:
            def esc(x):
                x = "" if x is None else str(x)
                x = x.replace('"', '""')
                return f'"{x}"'
            lines.append(",".join([esc(u["id"]), esc(u["bezirk"]), esc(u["name"]), esc(u["detail"])]))
        csv_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"Unmatched: {csv_file}")

    print(f"\nSummary:")
    print(f"  Already had coordinates: {already_have_coords}")
    print(f"  Newly matched: {matched_count}")
    print(f"  Unmatched: {len(unmatched)}")
    print(f"  Total: {len(data['bruecken'])}")


if __name__ == "__main__":
    main()

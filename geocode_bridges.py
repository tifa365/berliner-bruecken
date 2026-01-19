#!/usr/bin/env python3
"""
Geocode Berlin bridges from multiple sources:
1. Wikipedia bridge list (A-Z subpages)
2. Berlin WFS Detailnetz (official geodata)

Processes ALL bridge data files:
- bruecken_tagesspiegel.json (flat list)
- bruecken.json (bezirke + erhaltungsmassnahmen)

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
WIKI_SEGMENTS = ["A", "B", "CD", "E", "F", "G", "H", "IJ", "K", "L", "M", "N", "O", "PQ", "R", "S", "T", "UV", "W", "XYZ"]

WFS_URL = "https://gdi.berlin.de/services/wfs/detailnetz"

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

    repl = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"}
    for k, v in repl.items():
        s = s.replace(k, v)

    # Expand common abbreviations
    abbrevs = {
        " d. ": " der ",
        " d.": " der ",
        "nördl.": "noerdliche",
        "südl.": "suedliche",
        "östl.": "oestliche",
        "westl.": "westliche",
        "br.": "bruecke",
        "str.": "strasse",
        "bw.": "bauwerk ",
        "bw ": "bauwerk ",
        "uebb": "ueberbau",
        "übb": "ueberbau",
        "fgb ": "fussgaengerbruecke ",
        "laakebruecke": "laake-bruecke",  # Handle "Laakebrücke" vs "Laake-Brücke"
    }
    s_lower = s.lower()
    for abbr, full in abbrevs.items():
        s_lower = s_lower.replace(abbr, full)
    s = s_lower

    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
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
    """Build index: normalized_bridge_name -> dict(lat, lon, source_url, raw_name)"""
    print("Building Wikipedia bridge index...")
    index = {}

    for seg in WIKI_SEGMENTS:
        try:
            html = fetch_wiki_segment(seg)
        except Exception as e:
            print(f"  Warning: Failed to fetch segment {seg}: {e}")
            continue

        soup = BeautifulSoup(html, "lxml")
        tables = soup.select("table.wikitable")
        if not tables:
            continue

        for table in tables:
            for row in table.select("tr"):
                cells = row.select("td")
                if len(cells) < 5:
                    continue

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


def build_wfs_index() -> dict:
    """Build index from Berlin WFS Detailnetz (official geodata)."""
    print("Building WFS bridge index...")
    index = {}

    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": "detailnetz:b_bauwerke",
        "outputFormat": "json",
        "srsName": "EPSG:4326",
        "CQL_FILTER": "bauwerksart='BR'"  # Only bridges
    }

    try:
        r = requests.get(WFS_URL, params=params, headers=UA, timeout=120)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  Warning: Failed to fetch WFS data: {e}")
        return index

    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        name = props.get("bauwerksname", "")

        if not name or not geom:
            continue

        # Get centroid of geometry (LineString or MultiLineString)
        coords = geom.get("coordinates", [])
        if not coords:
            continue

        # Handle MultiLineString
        if geom.get("type") == "MultiLineString":
            all_points = [pt for line in coords for pt in line]
        elif geom.get("type") == "LineString":
            all_points = coords
        else:
            continue

        if not all_points:
            continue

        # Calculate centroid
        lon = sum(p[0] for p in all_points) / len(all_points)
        lat = sum(p[1] for p in all_points) / len(all_points)

        key = normalize_name(name)
        index[key] = {
            "lat": lat,
            "lon": lon,
            "source": "WFS Detailnetz Berlin",
            "raw_name": name,
            "bauwerksnummer": props.get("bauwerksnummer", ""),
        }

    print(f"  Found {len(index)} bridges with coordinates")
    return index


def match_bridge(bridge: dict, wiki_index: dict, wfs_index: dict, name_field: str = "name") -> dict | None:
    """Try to match a bridge against wiki and WFS indices."""
    name = bridge.get(name_field, "")
    if not name:
        return None

    def search_indices(key: str) -> dict | None:
        """Search both indices for a key, prefer Wikipedia."""
        if key in wiki_index:
            return wiki_index[key]
        if key in wfs_index:
            return wfs_index[key]
        return None

    def fuzzy_search_wfs(search_key: str) -> dict | None:
        """Fuzzy search WFS index - find entries containing search_key."""
        for wfs_key, data in wfs_index.items():
            if search_key in wfs_key or wfs_key in search_key:
                return data
        return None

    # Try exact match first
    key = normalize_name(name)
    hit = search_indices(key)
    if hit:
        return hit

    # Try without suffixes like "Südost", "Nordwest", "Überbau 1", etc.
    base_name = re.sub(r"\s+(südost|nordwest|nord|süd|ost|west|überbau\s*\d+|teilbauwerk\s*\d+|bauwerk\s*\d+[a-z]?|gewölbe.*|galerie.*)$", "", name, flags=re.IGNORECASE)
    if base_name != name:
        key = normalize_name(base_name)
        hit = search_indices(key)
        if hit:
            return hit

    # Try with common variations
    variations = [
        name.replace("-", " "),
        name.replace(" ", "-"),
        re.sub(r"brücke$", "bruecke", name, flags=re.IGNORECASE),
        re.sub(r"straße", "strasse", name, flags=re.IGNORECASE),
        # Try partial match for "Fußgängerbrücke X" -> "X"
        re.sub(r"^(Fußgängerbrücke|Fussgangerbrucke)\s+", "", name, flags=re.IGNORECASE),
        # Convert "östlicher Teil" to "ÜBB Ost" style
        re.sub(r"östlicher Teil$", "ÜBB Ost", name, flags=re.IGNORECASE),
        re.sub(r"westlicher Teil$", "ÜBB West", name, flags=re.IGNORECASE),
        re.sub(r"nördlicher Teil$", "ÜBB Nord", name, flags=re.IGNORECASE),
        re.sub(r"südlicher Teil$", "ÜBB Süd", name, flags=re.IGNORECASE),
        re.sub(r"nordwestlicher Teil$", "ÜBB Nordwest", name, flags=re.IGNORECASE),
        re.sub(r"südöstlicher Teil$", "ÜBB Südost", name, flags=re.IGNORECASE),
        re.sub(r"nordöstlicher Teil$", "ÜBB Nordost", name, flags=re.IGNORECASE),
        re.sub(r"südwestlicher Teil$", "ÜBB Südwest", name, flags=re.IGNORECASE),
        # Also try the reverse
        re.sub(r"nördlicher Überbau$", "ÜBB Nord", name, flags=re.IGNORECASE),
        re.sub(r"südlicher Überbau$", "ÜBB Süd", name, flags=re.IGNORECASE),
        re.sub(r"mittlerer Überbau$", "ÜBB Mitte", name, flags=re.IGNORECASE),
    ]
    for var in variations:
        key = normalize_name(var)
        hit = search_indices(key)
        if hit:
            return hit

    # Try fuzzy matching against WFS (handles suffixes like "(Panke)", "(BW 10)")
    key = normalize_name(base_name if base_name != name else name)
    if len(key) >= 6:  # Only for meaningful names
        hit = fuzzy_search_wfs(key)
        if hit:
            return hit

    # Try extracting just the main bridge name (before any directional/structural suffix)
    # e.g., "Elsenbrücke nordwestlicher Teil" -> "Elsenbrücke"
    # e.g., "Märkische-Allee-Brücke Bauwerk 4 Überbau 1" -> "Märkische-Allee-Brücke"
    main_name = re.split(r'\s+(nordwest|südost|nordost|südwest|nord|süd|ost|west|nördlich|südlich|östlich|westlich|bauwerk|überbau|teilbauwerk|havelquerung|vorlandbrücke|uferbrücke)', name, flags=re.IGNORECASE)[0].strip()
    if main_name and main_name != name:
        key = normalize_name(main_name)
        if len(key) >= 6:
            hit = fuzzy_search_wfs(key)
            if hit:
                return hit

    return None


def geocode_tagesspiegel(wiki_index: dict, wfs_index: dict) -> tuple[int, int, int, list]:
    """Geocode bruecken_tagesspiegel.json"""
    input_file = Path("bruecken_tagesspiegel.json")
    if not input_file.exists():
        print(f"  Skipping {input_file} (not found)")
        return 0, 0, 0, []

    print(f"\nProcessing {input_file}...")
    data = json.loads(input_file.read_text(encoding="utf-8"))

    unmatched = []
    matched_count = 0
    already_have_coords = 0

    for b in data["bruecken"]:
        if b.get("lat") is not None and b.get("lon") is not None:
            already_have_coords += 1
            continue

        hit = match_bridge(b, wiki_index, wfs_index)
        if hit:
            b["lat"] = hit["lat"]
            b["lon"] = hit["lon"]
            source = hit.get("source", "Wikipedia")
            b["coord_quelle"] = f'{source}: {hit["raw_name"]}'
            matched_count += 1
        else:
            unmatched.append({
                "file": "bruecken_tagesspiegel.json",
                "id": b.get("id"),
                "bezirk": b.get("bezirk"),
                "name": b.get("name"),
                "detail": b.get("detail"),
            })

    output_file = Path("bruecken_tagesspiegel.json")
    output_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Updated: {output_file}")

    return already_have_coords, matched_count, len(data["bruecken"]), unmatched


def geocode_bruecken_json(wiki_index: dict, wfs_index: dict) -> tuple[int, int, int, list]:
    """Geocode bruecken.json (bezirke + erhaltungsmassnahmen)"""
    input_file = Path("bruecken.json")
    if not input_file.exists():
        print(f"  Skipping {input_file} (not found)")
        return 0, 0, 0, []

    print(f"\nProcessing {input_file}...")
    data = json.loads(input_file.read_text(encoding="utf-8"))

    unmatched = []
    matched_count = 0
    already_have_coords = 0
    total = 0

    # Process bezirke bridges
    for bezirk_data in data.get("bezirke", []):
        bezirk_name = bezirk_data.get("bezirk", "")
        for b in bezirk_data.get("bruecken", []):
            total += 1
            if b.get("lat") is not None and b.get("lon") is not None:
                already_have_coords += 1
                continue

            hit = match_bridge(b, wiki_index, wfs_index)
            if hit:
                b["lat"] = hit["lat"]
                b["lon"] = hit["lon"]
                source = hit.get("source", "Wikipedia")
                b["coord_quelle"] = f'{source}: {hit["raw_name"]}'
                matched_count += 1
            else:
                unmatched.append({
                    "file": "bruecken.json",
                    "section": "bezirke",
                    "bezirk": bezirk_name,
                    "name": b.get("name"),
                })

    # Process erhaltungsmassnahmen
    for b in data.get("erhaltungsmassnahmen", []):
        total += 1
        if b.get("lat") is not None and b.get("lon") is not None:
            already_have_coords += 1
            continue

        hit = match_bridge(b, wiki_index, wfs_index)
        if hit:
            b["lat"] = hit["lat"]
            b["lon"] = hit["lon"]
            source = hit.get("source", "Wikipedia")
            b["coord_quelle"] = f'{source}: {hit["raw_name"]}'
            matched_count += 1
        else:
            unmatched.append({
                "file": "bruecken.json",
                "section": "erhaltungsmassnahmen",
                "bezirk": b.get("bezirk"),
                "name": b.get("name"),
            })

    output_file = Path("bruecken.json")
    output_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Updated: {output_file}")

    return already_have_coords, matched_count, total, unmatched


def main():
    wiki_index = build_wiki_index()
    wfs_index = build_wfs_index()

    # Show combined index size
    combined_keys = set(wiki_index.keys()) | set(wfs_index.keys())
    print(f"\nCombined index: {len(combined_keys)} unique bridges")

    all_unmatched = []
    total_already = 0
    total_matched = 0
    total_bridges = 0

    # Geocode bruecken_tagesspiegel.json
    already, matched, total, unmatched = geocode_tagesspiegel(wiki_index, wfs_index)
    total_already += already
    total_matched += matched
    total_bridges += total
    all_unmatched.extend(unmatched)

    # Geocode bruecken.json
    already, matched, total, unmatched = geocode_bruecken_json(wiki_index, wfs_index)
    total_already += already
    total_matched += matched
    total_bridges += total
    all_unmatched.extend(unmatched)

    # Write unmatched report
    if all_unmatched:
        csv_file = Path("unmatched_bridges.csv")
        lines = ["file,section,bezirk,name"]
        for u in all_unmatched:
            def esc(x):
                x = "" if x is None else str(x)
                x = x.replace('"', '""')
                return f'"{x}"'
            lines.append(",".join([
                esc(u.get("file")),
                esc(u.get("section", "")),
                esc(u.get("bezirk")),
                esc(u.get("name")),
            ]))
        csv_file.write_text("\n".join(lines), encoding="utf-8")
        print(f"\nUnmatched bridges: {csv_file}")

    print(f"\n{'='*50}")
    print(f"SUMMARY")
    print(f"{'='*50}")
    print(f"  Already had coordinates: {total_already}")
    print(f"  Newly matched:           {total_matched}")
    print(f"  Unmatched:               {len(all_unmatched)}")
    print(f"  Total bridges:           {total_bridges}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

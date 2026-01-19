# Berliner Brücken

Daten zu maroden und sanierungsbedürftigen Brücken in Berlin, basierend auf dem **Masterplan Brücken 2025-2040** der Senatsverwaltung.

## Datensätze

### 1. bruecken.json

Umfassende Daten zu **175 Ersatzneubauten** und **19 Erhaltungsmaßnahmen** mit:
- Baujahr
- Geplanter Baubeginn/Bauende
- Geschätzte Kosten (Mio. Euro)
- Status (im_bau, in_planung, noch_nicht_terminiert)

**Zusammenfassung (Masterplan):**
| Kategorie | Anzahl | Kosten |
|-----------|--------|--------|
| Ersatzneubauten | 175 | 1,7 Mrd. Euro |
| Erhaltungsmaßnahmen | 125 | 125 Mio. Euro |
| **Gesamt** | **300** | **1,8 Mrd. Euro** |

**Bezirke nach Anzahl Neubauten:**
| Bezirk | Brücken |
|--------|---------|
| Marzahn-Hellersdorf | 49 |
| Pankow | 28 |
| Treptow-Köpenick | 18 |
| Spandau | 15 |
| Friedrichshain-Kreuzberg | 13 |
| Lichtenberg | 12 |
| Mitte | 12 |
| Charlottenburg-Wilmersdorf | 10 |
| Steglitz-Zehlendorf | 4 |
| Tempelhof-Schöneberg | 4 |
| Neukölln | 1 |
| Reinickendorf | 1 |

---

### 2. kaputte_bruecken.json

**73 beschädigte Brücken** mit Geokoordinaten (lat/lon) und Schadensklassifizierung.

| Schaden | Typ | Anzahl |
|---------|-----|--------|
| 1 | Koppelfugenproblematik | 6 |
| 2 | AKR-Problematik (Betonkrebs) | 3 |
| 3 | Spannungsrisskorrosion | 50 |
| 4 | Spannungsrisskorrosion + Koppelfugenproblematik | 6 |
| 5 | Spannungsrisskorrosion + AKR-Problematik | 8 |

---

## Quellen

### Berliner Zeitung (17.01.2026)
- **Artikel:** "Neuer Masterplan für Berlin: Diese Straßenbrücken stehen vor dem Aus"
- **Autor:** Peter Neumann
- **Archiv:** https://archive.ph/QXd9g
- **Basis:** Masterplan Brücken 2025 bis 2040 (Senatsverwaltung MVKU)

### Der Tagesspiegel (15.01.2026)
- **Archiv:** https://archive.ph/jEOtK

### Der Tagesspiegel (24.06.2025)
- **Artikel:** "„Ein Jahrzehnt der Baustellen": Autobahngesellschaft sorgt sich um 50 marode Brücken in Berlin"
- **Archiv:** https://archive.ph/eYYME
- **Daten:** Senatsverwaltung für Mobilität, Verkehr, Klimaschutz und Umwelt (SenMVKU)
- **Datawrapper:** https://datawrapper.dwcdn.net/pi3Oc/19/

---

## Hintergrund

Berlin hat etwa **2.700 Brücken** (nach Eigentümer):
- ~33% Land Berlin (1.047 Bauwerke an 913 Standorten)
- ~28% Deutsche Bahn
- ~25% BVG
- ~15% Autobahn GmbH des Bundes
- ~2% Wasser- und Schifffahrtsbehörden

### Zustand der Berliner Brücken
- **19%** gut oder sehr gut
- **27%** ausreichend
- **7%** nicht ausreichend

### Ursachen
Viele Brücken wurden in den 1970er-80er Jahren aus Spannbeton gebaut. Probleme:
- **Hennigsdorfer Spannstahl** (DDR): anfällig für Spannungsrisskorrosion
- **Sigma-Spannstahl** (Westdeutschland): vergleichbare Probleme
- Beide Stahlarten an **72 Brückenstandorten** in Berlin verbaut

### Kapazitäten
- Nur **48 Stellen** in der Abteilung Tiefbau der Senatsverkehrsverwaltung
- Aktuell: 4-6 Projekte pro Jahr möglich
- Erforderlich: ~20 Projekte pro Jahr

---

## Weitere Ressourcen

- [Brückenbau Berlin](https://www.berlin.de/sen/uvk/mobilitaet-und-verkehr/infrastruktur/brueckenbau/) (Senatsverwaltung MVKU)
- [Liste der Brücken in Berlin](https://de.wikipedia.org/wiki/Liste_der_Br%C3%BCcken_in_Berlin) (Wikipedia)

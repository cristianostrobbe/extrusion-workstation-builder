"""Parametric cut list / BoM for a 3D-printer workstation frame (no doors).

Layout (front view):            Two printer towers (P1S-size volume + AMS on top),
                                storage shelves below
   +---------+---------+
   |  tower  |  tower  |
   |  (P1S)  |  (P1S)  |
   +---------+---------+  <- deck
   |  shelf  |  shelf  |
   +---------+---------+  <- mid shelf
   |  shelf  |  shelf  |
   +---------+---------+  <- bottom, on 6 leveling casters

Frame: 3030 (30 series EU, 8 mm slot) profile, butt-jointed with TPEA corner brackets
(one under each beam end, fixed with M6x12 + washer + drop-in T-nut).
Posts run full height; every beam sits between two posts (length = gap).
All dimensions in mm. Edit the parameters and run: python3 frame_bom.py
"""
from collections import Counter

P = 30            # profile size (3030)
LEFT_IN = 420     # clear width of tower bay (P1S body is 389 mm wide)
RIGHT_IN = 420    # clear width of right bay (same as left, so it also takes a P1S)
RIGHT_TOWER = True  # right bay also rises to TOTAL_H as a second printer tower
DEPTH = 420       # overall depth: P1S body 389 mm + margin
LOW_H = 600       # lower frame height (post bottom to top of the deck beam)
TOTAL_H = 1150    # tower frame height: 508 mm clear above the deck panel = P1S 458 mm + 50 mm
LOW_LEVELS = 3    # bottom, mid shelf, deck

width_total = LEFT_IN + RIGHT_IN + 3 * P
y_beam = DEPTH - 2 * P

cuts = Counter()
cuts[("post tall", TOTAL_H)] += 6 if RIGHT_TOWER else 4        # left + middle (+ right) posts
if not RIGHT_TOWER:
    cuts[("post short", LOW_H)] += 2                             # right posts
cuts[("X beam left", LEFT_IN)] += 2 * (LOW_LEVELS + 1)           # front+back, 3 low levels + tower top
cuts[("X beam right", RIGHT_IN)] += 2 * (LOW_LEVELS + (1 if RIGHT_TOWER else 0))
cuts[("Y beam", y_beam)] += 3 * LOW_LEVELS + (3 if RIGHT_TOWER else 2)   # 3 per low level + tower top(s)

beam_ends = 2 * sum(n for (name, _), n in cuts.items() if "beam" in name)
brackets = beam_ends               # TPEA-308-3030: 1 under each beam end, 2 screws each
posts = sum(n for (name, _), n in cuts.items() if "post" in name)
panels = Counter()   # flush with outer faces, meet on the middle beam's centre line, notched for posts
panels[(LEFT_IN + 1.5 * P, DEPTH)] += LOW_LEVELS + 1
panels[(RIGHT_IN + 1.5 * P, DEPTH)] += LOW_LEVELS + (1 if RIGHT_TOWER else 0)
panel_fixings = 3 * sum(panels.values())   # front, back and outer beam slot (not the shared middle beam)
caster_fixings = 2 * posts         # each TPRE end cap clamps the post with 2 x M6x12 + T-nut
SPARE = 1.10                       # order ~10% extra small parts


def order(n):
    return int(-(-n * SPARE // 5) * 5)   # +10%, rounded up to a multiple of 5


hw = [
    (brackets, "TPEA-308-3030", "die-cast corner bracket, 30 series"),
    (2 * brackets + caster_fixings + panel_fixings, "TPAH-N-8-M6", "M6 drop-in T-nut, 30 series"),
    (2 * brackets + caster_fixings, "EDLG-S1-M6-L12", "M6x12 button head screw (brackets, end caps)"),
    (panel_fixings, "EDLJ-S1-M6-L20", "M6x20 countersunk socket screw DIN 7991 (panels, flush)"),
    (2 * brackets, "EPDA-S1W-B-6", "M6 flat washer (brackets)"),
    (posts, "TPRE-G306-3030-M8", "end cap with M8 female thread (caster mount)"),
    (posts, "DEPN-W2-40-N", "leveling caster, M8 stem, 50 kg, H 71 mm"),
]

print(f"Overall: {width_total} W x {DEPTH} D x {TOTAL_H} H mm (+95 mm end cap + caster)\n")
print("CUT LIST (3030, cut to length, ends square)")
total = 0
for (name, length), n in sorted(cuts.items(), key=lambda kv: -kv[0][1]):
    print(f"  {n:>3} x {length:>5} mm  {name}")
    total += n * length
print(f"  pieces: {sum(cuts.values())}, total length: {total / 1000:.2f} m\n")
print("HARDWARE (needed -> order)")
for n, pn, desc in hw:
    q = n if pn.startswith(("TPRE", "DEPN")) else order(n)
    print(f"  {n:>3} -> {q:>3} x {pn:<18} {desc}")
print("PANELS (12 mm plywood/MDF, buy locally)")
for (w, d), n in panels.items():
    print(f"  {n:>3} x {w:.0f} x {d:.0f} mm  (corner notches 30x30 outer, 15x30 at middle post)")


# ---------- JLCMC order BoM (official template columns, upload at jlcmc.com "BOM / RFQ") ----------
def jlcmc_rows():
    rows = []
    by_len = {}
    for (name, length), n in cuts.items():               # merge members that share a cut length
        q, names = by_len.get(length, (0, []))
        by_len[length] = (q + n, names + [f"{n}x {name}"])
    for length, (n, names) in sorted(by_len.items(), reverse=True):
        rows.append((f"TXCK-H6-3030-L{length:.0f}",
                     f"Aluminum extrusion EU 30 series 3030, 8 mm slot, natural sandblasted anodized, "
                     f"cut to {length:.0f} mm", n, f"{' + '.join(names)}; ends square, no machining"))
    for n, pn, desc in hw:
        q = n if pn.startswith(("TPRE", "DEPN")) else order(n)
        rows.append((pn, desc, q, f"needed {n}" + (f", +{q - n} spare" if q > n else "")))
    return [(f"WS-{i:02d}", pn, desc, q, rem) for i, (pn, desc, q, rem) in enumerate(rows, 1)]


def write_xlsx(path, header, rows):
    """Minimal single-sheet .xlsx (stdlib only) matching JLCMC_BOM_Template.xlsx columns."""
    import zipfile
    from xml.sax.saxutils import escape

    def cell(ref, v):
        if isinstance(v, (int, float)):
            return f'<c r="{ref}"><v>{v}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(v))}</t></is></c>'

    xml_rows = []
    for r, vals in enumerate([header] + rows, 1):
        xml_rows.append(f'<row r="{r}">' + "".join(cell(f"{'ABCDE'[c]}{r}", v) for c, v in enumerate(vals)) + "</row>")
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<cols><col min="1" max="1" width="14" customWidth="1"/><col min="2" max="2" width="24" customWidth="1"/>'
             '<col min="3" max="3" width="90" customWidth="1"/><col min="4" max="4" width="10" customWidth="1"/>'
             '<col min="5" max="5" width="40" customWidth="1"/></cols>'
             f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>')
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": sheet,
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


if __name__ == "__main__":
    import csv
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    header = ["*Customer Part #", "JLCMC Part #", "*Product Description", "*Quantity", "Remark"]
    rows = jlcmc_rows()
    write_xlsx(os.path.join(here, "jlcmc_bom.xlsx"), header, rows)
    with open(os.path.join(here, "jlcmc_bom.csv"), "w", newline="") as f:
        csv.writer(f).writerows([header] + rows)
    print(f"\nWrote jlcmc_bom.xlsx / jlcmc_bom.csv ({len(rows)} lines)")

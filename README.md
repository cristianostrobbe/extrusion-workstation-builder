# Extrusion Workstation Builder

A 3D-printer workstation built from 3030 aluminium extrusion: two printer towers, each sized for a Bambu Lab P1S with an AMS on top, with two storage shelves below, on leveling casters. Frame 930 × 420 × 1150 mm. No drilling or tapping of the aluminium; everything joins with die-cast corner brackets and drop-in T-nuts.

**Configurator:** https://cristianostrobbe.github.io/extrusion-workstation-builder/

The configurator lets you change the bays, heights, finish, casters, shelves and an optional acrylic enclosure, and checks that your printer fits. It produces:
- a JLCMC order list (.xlsx in JLCMC's BOM / RFQ upload format, or .csv)
- a STEP model of the frame and panels
- 1:1 DXF drawings of every panel, sorted into `floor/`, `side_panels/` and `doors/`
- a shipping estimate, with the option to buy the profiles or acrylic locally

Prices come from the jlcmc.com price API (November 2026) and exclude shipping and VAT.

## Files

| Path | What it is |
|---|---|
| `web/index.html` | The configurator, a single self-contained page |
| `web/build.py` | Wraps the page into `docs/index.html` for GitHub Pages |
| `frame_bom.py` | Parametric cut list and hardware list; writes `jlcmc_bom.xlsx` and `jlcmc_bom.csv` |
| `cad/workstation.py` | Parametric FreeCAD model; writes `workstation.FCStd`, `workstation.step` and the panel DXFs in `cad/panels/` |
| `BOM.md` | The default build: priced parts list, panel files and clear dimensions |

## Rebuilding

```sh
python3 frame_bom.py                       # BoM files
freecadcmd cad/workstation.py              # FreeCAD model, STEP and DXFs (FreeCAD 1.x)
python3 web/build.py                       # docs/index.html after editing web/index.html
```

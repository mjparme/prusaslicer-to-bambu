# PrusaSlicer G-code (reference only)

These `.gcode` files are the converted start/end scripts for the Bambu Lab A1 (Orca/Bambu placeholders rewritten for PrusaSlicer syntax).

**You do not need to load these files manually.** The G-code is already embedded in the printer profiles at the repo root (`config-a1-*.ini`) as `start_gcode` and `end_gcode`. Import a config bundle and PrusaSlicer uses that inline G-code automatically.

These files are kept here for reference — easier to read, diff, and edit than the escaped single-line values inside the `.ini` files. After changing a file here, copy the updated content into the matching profile field in PrusaSlicer (or update the `.ini` and re-import).

| File | Used by |
|------|---------|
| `ps-a1-start-textured.gcode` | `config-a1-textured.ini` |
| `ps-a1-start-smooth.gcode` | `config-a1-smooth.ini` |
| `ps-a1-start-fast-textured.gcode` | `config-a1-textured-fast.ini` |
| `ps-a1-start-fast-smooth.gcode` | `config-a1-smooth-fast.ini` |
| `ps-a1-end.gcode` | All four configs |

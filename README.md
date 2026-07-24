# PrusaSlicer → Bambu Lab A1

PrusaSlicer printer profiles and custom G-code for printing on a **Bambu Lab A1** (single spool, no AMS). Start, end, and layer-change scripts were converted from Bambu Studio / OrcaSlicer placeholders to PrusaSlicer syntax while keeping Bambu firmware commands intact.

## Requires BamBuddy

This workflow depends on a running [**BamBuddy**](https://wiki.bambuddy.cool) installation to send prints to your A1 and archive jobs. PrusaSlicer does not connect to Bambu printers over the network on its own.

- **Install:** [Installation guide](https://wiki.bambuddy.cool/getting-started/installation/)
- **Quick start:** [Getting started](https://wiki.bambuddy.cool/getting-started/) (enable Developer Mode on the printer, add the A1, insert an SD card)

After BamBuddy is up, add your printer in the BamBuddy UI. Printing is handled automatically by a **post-processing script** (see below) — you slice and export as usual in PrusaSlicer, then start the job from BamBuddy.

## Sending prints to BamBuddy

PrusaSlicer cannot send jobs to a Bambu printer directly, and BamBuddy only accepts **`.gcode.3mf`** uploads (not plain `.gcode`). A post-processing script bridges the gap.

**Script:** `scripts/prusaslicer-to-bambuddy.py` in this repo (configured in the imported `.ini` files as `post_process`)

Clone the repo to `~/prusaslicer-to-bambu` so the default path works:

```bash
git clone https://github.com/mjparme/prusaslicer-to-bambu.git ~/prusaslicer-to-bambu
```

The configs use `$HOME/prusaslicer-to-bambu/scripts/prusaslicer-to-bambuddy.py`. The text box shows that literal string — PrusaSlicer does not expand it in the UI. On **macOS/Linux**, the shell expands `$HOME` when the script runs at export time. On **Windows**, use a full path instead (see below).

After each slice/export, the script:

1. Reads the exported `.gcode` from PrusaSlicer
2. Wraps it in a minimal `.gcode.3mf` zip (`Metadata/plate_1.gcode` + `slice_info.config`)
3. Extracts the embedded PNG thumbnail from the G-code comments and adds `Metadata/plate_1.png` (so BamBuddy shows a preview in the library)
4. Uploads the package to BamBuddy via `POST /api/v1/library/files`
5. Optionally adds the file to the BamBuddy print queue

You then open BamBuddy and print from the library or queue as you would with any other job.

### PrusaSlicer setup

The imported configs already include:

- **Printer Settings → Post-processing scripts:** `$HOME/prusaslicer-to-bambu/scripts/prusaslicer-to-bambuddy.py`
- **Printer Settings → Firmware → G-code thumbnails:** `220x220/PNG` (required for library previews; QOI thumbnails are skipped)

#### Post-processing script path

| Platform | Default in configs | Notes |
|----------|-------------------|-------|
| macOS / Linux | `$HOME/prusaslicer-to-bambu/scripts/prusaslicer-to-bambuddy.py` | Clone repo to `~/prusaslicer-to-bambu`. `$HOME` is expanded by the shell when exporting — not by PrusaSlicer in the UI. Avoid `~`; use `$HOME` or an absolute path. |
| Windows | *(not preset)* | PrusaSlicer runs the script directly with no shell expansion. Set a full path, e.g. `C:\Users\you\prusaslicer-to-bambu\scripts\prusaslicer-to-bambuddy.py` |

If you clone the repo somewhere other than `~/prusaslicer-to-bambu` on Mac/Linux, update **Printer Settings → Post-processing scripts** (absolute path, quoted if it contains spaces) or add a symlink: `ln -s /path/to/repo ~/prusaslicer-to-bambu`.

PrusaSlicer has no `user.home`-style placeholder for `post_process` — that field is not processed through the `{macro}` system used in custom G-code.

### Script configuration

Environment variables (optional):

| Variable | Default | Purpose |
|----------|---------|---------|
| `BAMBUDDY_URL` | `http://localhost:8000` | BamBuddy server URL |
| `BAMBUDDY_FOLDER_ID` | *(unset)* | Upload to a specific library folder, e.g. `3` |
| `BAMBUDDY_ADD_TO_QUEUE` | `0` | Set to `1` to auto-add uploaded files to the print queue |

PrusaSlicer sets `SLIC3R_PP_OUTPUT_NAME` when invoking post-processing scripts; the script uses that to derive a clean `.gcode.3mf` filename instead of PrusaSlicer's temp path.

### Typical workflow

1. Slice and export in PrusaSlicer (or **Export G-code** / **Send to printer** — any action that runs post-processing)
2. Check the PrusaSlicer console for `Uploaded to BamBuddy: …`
3. Open BamBuddy → **Library** (or **Queue** if `BAMBUDDY_ADD_TO_QUEUE=1`)
4. Select the job and send it to your A1

## Requirements

- **Printer:** Bambu Lab A1 (tested without AMS)
- **Slicer:** PrusaSlicer 2.9.x (configs exported from 2.9.6)
- **G-code flavor:** Marlin (legacy) — set automatically by the imported profiles
- **Plate:** Textured or smooth PEI (see below)

## Import the configs

1. Open PrusaSlicer.
2. **File → Import → Import Config Bundle…** and choose one of the `.ini` files in this repo, **or** drag an `.ini` onto the PrusaSlicer window.
3. Pick the imported printer profile from the printer dropdown when slicing.

### Available profiles

| Config file | Printer profile name | Start G-code |
|-------------|---------------------|--------------|
| `config-a1-textured.ini` | Bambu Lab A1 - Textured Plate | Full start (textured PEI) |
| `config-a1-smooth.ini` | Bambu Lab A1 - Smooth Plate | Full start (smooth PEI) |
| `config-a1-textured-fast.ini` | Bambu Lab A1 - Textured Plate (Fast) | Fast start (textured PEI) |
| `config-a1-smooth-fast.ini` | Bambu Lab A1 - Smooth Plate (Fast) | Fast start (smooth PEI) |

The full and fast variants are otherwise identical — same print settings, end G-code, and layer-change G-code.

## Textured vs smooth

The only difference between the textured and smooth profiles is a single line in the **start G-code**:

- **Textured PEI** includes `G29.1 Z-0.02` — lowers the nozzle slightly because homing touches the top of the texture, not the bare plate.
- **Smooth PEI** omits that line entirely.

Use the profile that matches the plate on your printer. Mixing them (e.g. smooth profile on a textured plate) will affect first-layer height and adhesion.

## Fast start variant

The fast profiles swap in a shortened start sequence (`prusaslicer/ps-a1-start-fast-textured.gcode` or `ps-a1-start-fast-smooth.gcode`). This cuts several minutes off startup compared to the full Bambu-style start.

**Skipped:** startup sound, AMS purge/wipe-shake, auto extrude calibration, mech-mode check, nozzle wipe/brush/touching, `G29` bed probe, extrude-calibration lines.

**Kept:** heat bed and nozzle, `G28` homing, wait for temps, short prime line, `G29.1` plate offset (textured only), filament runout detection, `M1007 S1` (mass estimation), `G29.4` (reuse stored bed mesh).

**Use fast start when:**

- The bed was leveled recently (full start or screen calibration)
- The nozzle is reasonably clean
- You are reprinting with the same filament

**Switch back to the full start when:**

- You changed the nozzle or swapped plates
- You have adhesion or first-layer problems
- It has been a while since the last full bed probe

The fast variants have been sliced successfully but are less thoroughly print-tested than the full start.

## Repository layout

```
config-a1-*.ini          PrusaSlicer config bundles (import these)
scripts/
  prusaslicer-to-bambuddy.py   Post-processing: wrap gcode → upload to BamBuddy
prusaslicer/             Converted G-code for PrusaSlicer
  ps-a1-start-textured.gcode
  ps-a1-start-smooth.gcode
  ps-a1-start-fast-textured.gcode
  ps-a1-start-fast-smooth.gcode
  ps-a1-end.gcode
orca/                    Original Orca/Bambu G-code (reference)
```

To customize start G-code, edit the `.gcode` files under `prusaslicer/` and paste the contents into **Printer Settings → Custom G-code → Start G-code**, or regenerate the `.ini` files.

## Notes

- **Non-AMS only** — profiles are validated for a single spool. AMS-specific purge blocks in the full start are left as-is from the Orca source; the fast start uses a minimal non-AMS prime instead.
- **Bed leveling** — PrusaSlicer has no send-time “bed leveling” toggle like Bambu Studio. The full start runs `G29` when the printer’s `g29_before_print_flag` is set; the fast start assumes a stored mesh via `G29.4`. Run a full start or calibrate from the printer screen (**Settings → Maintenance → Calibration → Auto Bed Leveling**) when needed.
- **Placeholder conversion** — Orca/Bambu template variables were mapped to PrusaSlicer syntax (e.g. `first_layer_print_size` → `first_layer_print_max - first_layer_print_min`). See the `bambu-orca-to-ps` skill in [common-files](https://github.com/mjparme/common-files) for the conversion reference.

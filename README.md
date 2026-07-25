# PrusaSlicer → Bambu Lab A1

PrusaSlicer printer profiles and custom G-code for printing on a **Bambu Lab A1** (single spool, no AMS). Start, end, and layer-change scripts were converted from Bambu Studio / OrcaSlicer placeholders to PrusaSlicer syntax while keeping Bambu firmware commands intact.

## Getting Started

### 1. Set up BamBuddy

This workflow depends on a running [**BamBuddy**](https://wiki.bambuddy.cool) installation to send prints to your A1 and archive jobs. PrusaSlicer does not connect to Bambu printers over the network on its own.

1. Install BamBuddy - [installation guide](https://wiki.bambuddy.cool/getting-started/installation/)
2. Follow the [getting started](https://wiki.bambuddy.cool/getting-started/) steps (enable Developer Mode on the printer, add the A1, insert an SD card)
3. Add your printer in the BamBuddy UI

### 2. (Optional) Set up authentication

Skip this if BamBuddy runs without authentication (common on a trusted LAN).

If auth is enabled on your BamBuddy instance:

1. In BamBuddy, go to **Settings → API Keys** and create a key with **Manage Library** (and **Manage Queue** if you plan to use `BAMBUDDY_ADD_TO_QUEUE=1`)
   - `BAMBUDDY_ADD_TO_QUEUE=1` is an optional environment variable that tells the post-processing script to add each uploaded file to the BamBuddy print queue automatically after upload, instead of only placing it in the library
2. Set `BAMBUDDY_API_KEY` in the environment PrusaSlicer inherits when it runs post-processing - e.g. via `launchctl setenv` on macOS, or in a small wrapper script
   - **macOS and Linux:** If you launch PrusaSlicer from Finder, the Dock, or a desktop launcher, it does **not** load variables from `~/.zshrc`, `~/.bashrc`, or similar shell profiles. Post-processing scripts inherit PrusaSlicer's environment, not your interactive terminal. Putting `export BAMBUDDY_API_KEY=…` in a shell profile alone is not enough unless you also launch PrusaSlicer from that terminal, use `launchctl setenv BAMBUDDY_API_KEY …` (macOS), or point **Post-processing scripts** at a wrapper that exports the key and then runs `prusaslicer-to-bambuddy.py`. Quit and reopen PrusaSlicer after changing GUI-visible env vars. See [PrusaSlicer forum: GUI vs shell environment](https://forum.prusa3d.com/forum/prusaslicer/python-error-when-trying-to-run-post-processing-script/) and [Stack Overflow: macOS GUI apps and shell env vars](https://stackoverflow.com/questions/63206544/an-ide-does-not-respect-environment-variable-in-macos).

The post-processing script sends the key as an `X-API-Key` header. Do not store API keys in imported `.ini` files or commit them to git.

### 3. Clone the repo and import configs

Clone to `~/prusaslicer-to-bambu` so the default post-processing path resolves:

```bash
git clone https://github.com/mjparme/prusaslicer-to-bambu.git ~/prusaslicer-to-bambu
```

Import one or more configs into PrusaSlicer (import all four if you want every plate/start variant available):

1. Open PrusaSlicer
2. **File → Import → Import Config…** and choose one or more `config-a1-*.ini` files from this repo
3. Pick the imported printer profile from the printer dropdown when slicing

**Expected import warning:** PrusaSlicer shows an alert that the config contains a post-processing script and asks you to review it before exporting G-code. That warning is reasonable - **read `scripts/prusaslicer-to-bambuddy.py` in this repo first** (it wraps G-code for BamBuddy upload; see step 4), then click **OK** once you are satisfied with what it does.

| Config file | Printer profile name | Start G-code |
|-------------|---------------------|--------------|
| `config-a1-textured.ini` | Bambu Lab A1 - Textured Plate | Full start (textured PEI) |
| `config-a1-smooth.ini` | Bambu Lab A1 - Smooth Plate | Full start (smooth PEI) |
| `config-a1-textured-fast.ini` | Bambu Lab A1 - Textured Plate (Fast) | Fast start (textured PEI) |
| `config-a1-smooth-fast.ini` | Bambu Lab A1 - Smooth Plate (Fast) | Fast start (smooth PEI) |

The full and fast variants are otherwise identical - same print settings, end G-code, and layer-change G-code. Use the profile that matches your plate type (see [Textured vs smooth](#textured-vs-smooth) below).

### 4. Set up the post-processing script

The imported configs already wire up BamBuddy upload. PrusaSlicer cannot send jobs to a Bambu printer directly, and BamBuddy only accepts **`.gcode.3mf`** uploads (not plain `.gcode`). The script `scripts/prusaslicer-to-bambuddy.py` bridges the gap.

Verify these settings after import:

- **Print Settings → Output Options → Post-processing scripts:** `$HOME/prusaslicer-to-bambu/scripts/prusaslicer-to-bambuddy.py`
- **Printers → General → Firmware → G-code thumbnails:** `220x220/PNG` (required for library previews)

If you cloned the repo somewhere other than `~/prusaslicer-to-bambu`, update the post-processing path in **Print Settings → Output Options → Post-processing scripts** to match (or symlink: `ln -s /path/to/repo ~/prusaslicer-to-bambu`). On **Windows**, use a full path - see [Post-processing script path](#post-processing-script-path).

**Typical workflow:**

1. Slice and export in PrusaSlicer (or **Export G-code** / **Send to printer** - any action that runs post-processing)
2. Open BamBuddy → **Library** (or **Queue** if `BAMBUDDY_ADD_TO_QUEUE=1`)
3. Select the job and send it to your A1

## Additional Information

### How the post-processing script works

After each slice/export, `scripts/prusaslicer-to-bambuddy.py`:

1. Reads the exported `.gcode` from PrusaSlicer
2. Wraps it in a minimal `.gcode.3mf` zip (`Metadata/plate_1.gcode` + `slice_info.config`)
3. Extracts the embedded PNG thumbnail from the G-code comments and adds `Metadata/plate_1.png` (so BamBuddy shows a preview in the library)
4. Uploads the package to BamBuddy via `POST /api/v1/library/files`
5. Optionally adds the file to the BamBuddy print queue

### Post-processing script path

The text box shows `$HOME/...` literally, PrusaSlicer does not expand it in the UI. On macOS/Linux, the shell expands `$HOME` when the script runs at export time.

| Platform | Default in configs | Notes |
|----------|-------------------|-------|
| macOS / Linux | `$HOME/prusaslicer-to-bambu/scripts/prusaslicer-to-bambuddy.py` | Clone repo to `~/prusaslicer-to-bambu`. Avoid `~`; use `$HOME` or an absolute path. |
| Windows | *(not preset)* | PrusaSlicer runs the script directly with no shell expansion. Set a full path, e.g. `C:\Users\you\prusaslicer-to-bambu\scripts\prusaslicer-to-bambuddy.py` |

PrusaSlicer has no `user.home`-style placeholder for `post_process` - that field is not processed through the `{macro}` system used in custom G-code.

### Script environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BAMBUDDY_URL` | `http://localhost:8000` | BamBuddy server URL |
| `BAMBUDDY_API_KEY` | *(unset)* | API key when BamBuddy auth is enabled |
| `BAMBUDDY_FOLDER_ID` | *(unset)* | Upload to a specific library folder, e.g. `3` |
| `BAMBUDDY_ADD_TO_QUEUE` | `0` | Set to `1` to auto-add uploaded files to the print queue |

PrusaSlicer sets `SLIC3R_PP_OUTPUT_NAME` when invoking post-processing scripts; the script uses that to derive a clean `.gcode.3mf` filename instead of PrusaSlicer's temp path.

**API key permissions** (when auth is enabled):

| Script action | Required permission |
|---------------|---------------------|
| Upload to library | **Manage Library** |
| Add to queue (`BAMBUDDY_ADD_TO_QUEUE=1`) | **Manage Library** + **Manage Queue** |

### Textured vs smooth

OrcaSlicer and Bambu Studio let you pick a plate type (textured vs smooth) from a dropdown; the start G-code applies the right `G29.1` offset via a `{curr_bed_type}` conditional. PrusaSlicer has no equivalent plate-type setting, so this repo uses **separate printer profiles** instead - pick the textured or smooth profile that matches the plate on your printer.

The only G-code difference between those profiles is a single line in the **start G-code**:

- **Textured PEI** includes `G29.1 Z-0.02` - lowers the nozzle slightly because homing touches the top of the texture, not the bare plate.
- **Smooth PEI** omits that line entirely.

Use the profile that matches the plate on your printer. Mixing them (e.g. smooth profile on a textured plate) will affect first-layer height and adhesion.

### Fast start variant

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

### Repository layout

```
config-a1-*.ini          PrusaSlicer configs (import these)
scripts/
  prusaslicer-to-bambuddy.py   Post-processing: wrap gcode → upload to BamBuddy
prusaslicer/             Converted G-code for PrusaSlicer (reference; also embedded in .ini)
orca/                    Original Orca/Bambu G-code (reference)
```

To customize start G-code, edit the `.gcode` files under `prusaslicer/` and paste the contents into **Printer Settings → Custom G-code → Start G-code**, or regenerate the `.ini` files.

### Notes

- **Non-AMS only** - profiles are validated for a single spool. AMS-specific purge blocks in the full start are left as-is from the Orca source; the fast start uses a minimal non-AMS prime instead.
- **Bed leveling** - PrusaSlicer has no send-time “bed leveling” toggle like Bambu Studio. The full start runs `G29` when the printer’s `g29_before_print_flag` is set; the fast start assumes a stored mesh via `G29.4`. Run a full start or calibrate from the printer screen (**Settings → Maintenance → Calibration → Auto Bed Leveling**) when needed.
- **Placeholder conversion** - Orca/Bambu template variables were mapped to PrusaSlicer syntax (e.g. `first_layer_print_size` → `first_layer_print_max - first_layer_print_min`). See the `bambu-orca-to-ps` skill in [common-files](https://github.com/mjparme/common-files) for the conversion reference.

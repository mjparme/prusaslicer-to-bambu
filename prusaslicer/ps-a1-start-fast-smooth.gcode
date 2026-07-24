;===== Bambu Lab A1 — FAST start (smooth PEI) ============================
; Same as ps-a1-start-fast-textured.gcode but without G29.1 plate offset.
; See header comments in that file for skipped steps and when to use.
;===== machine: A1 =========================

G392 S0
M9833.2

;===== heat bed and hotend (parallel) ==========
M1002 gcode_claim_action : 2
M1002 set_filament_type:{filament_type[0]}
M104 S{first_layer_temperature[0]}
M140 S{first_layer_bed_temperature[0]}

;===== machine reset ==========================
M204 S6000
M220 S100
M221 S100
M73.2   R1.0
M982.2 S1 ; cog noise reduction

;===== home ===================================
M1002 gcode_claim_action : 13
G28

;===== wait for temps =========================
M190 S{first_layer_bed_temperature[0]}
M109 S{first_layer_temperature[0]}

;===== minimal prime (non-AMS) ================
M211 X0 Y0 Z0 ; soft endstop off
M975 S1
M412 S1 ; filament runout detection

G90
M83
G1 X108.000 Y-0.500 F30000
G1 Z0.300 F1200
M400
G92 E0
G1 E8 F300
G1 E-0.5 F300

;===== smooth PEI — no G29.1 offset ===========

;===== ready to print =========================
M1002 gcode_claim_action : 0
M400

M960 S1 P0
M960 S2 P0
M106 S0
M106 P2 S0
M106 P3 S0

M975 S1
G90
M83
T1000

M1007 S1 ; mass estimation
G29.4

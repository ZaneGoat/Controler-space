"""
led_ui.py — Spaceship Cockpit Subsystem Console & Haptics Matrix.
Handles Warp Core Reactor (PS4 LED) telemetry and Propulsion Haptics (Rumble Diagnostics).
Can be embedded in main.py as a secondary cockpit HUD or launched standalone via led.py.
"""
import dearpygui.dearpygui as dpg
import threading
import time
import math

# ── Cockpit HUD Color Palette ────────────────────────────────────────────────
C_ALERT_RED    = [235, 35, 45, 255]
C_PLASMA_BLUE  = [35, 165, 255, 255]
C_WARP_GREEN   = [40, 255, 120, 255]
C_SOLAR_ORANGE = [255, 140, 25, 255]
C_CYBER_PURPLE = [190, 45, 255, 255]
C_WHITE_HOT    = [250, 250, 250, 255]
C_PANEL_BG     = [16, 16, 20, 255]
C_BORDER_NEON  = [95, 20, 25, 255]
C_TEXT_DIM     = [120, 120, 130, 255]
C_CORE_OFF     = [25, 6, 8, 255]

# Global animation and vibration state
_pulse_active = False
_pulse_thread = None
_vibe_thread = None
_stop_vibe_event = threading.Event()


def build_led_window(led_backend, standalone=False):
    """
    Builds the Starship Telemetry Console for Warp Core LED and Haptic Engine.
    """
    global _pulse_active

    # ── Internal Vibration Runner ─────────────────────────────────────────────
    def run_vibration_profile(profile_type):
        global _vibe_thread
        _stop_vibe_event.set()
        time.sleep(0.04)
        _stop_vibe_event.clear()

        def _worker():
            try:
                if profile_type == "warp_pulse":
                    dpg.configure_item("hud_vibe_status", default_value="WARP PULSE ACTIVE", color=C_PLASMA_BLUE)
                    led_backend.set_rumble(255, 0)
                    time.sleep(0.18)
                    led_backend.set_rumble(0, 0)

                elif profile_type == "engine_rumble":
                    dpg.configure_item("hud_vibe_status", default_value="SUBLIGHT THRUST TEST (1.2s)", color=C_SOLAR_ORANGE)
                    led_backend.set_rumble(60, 210)
                    for _ in range(12):
                        if _stop_vibe_event.is_set():
                            break
                        time.sleep(0.1)
                    led_backend.set_rumble(0, 0)

                elif profile_type == "hyperdrive_spool":
                    dpg.configure_item("hud_vibe_status", default_value="HYPERDRIVE FREQUENCY SWEEP", color=C_WARP_GREEN)
                    # Sweep up
                    for power in range(10, 255, 18):
                        if _stop_vibe_event.is_set():
                            break
                        led_backend.set_rumble(power, power // 2)
                        time.sleep(0.05)
                    # Sustain peak
                    if not _stop_vibe_event.is_set():
                        time.sleep(0.25)
                    # Sweep down
                    for power in range(255, 0, -25):
                        if _stop_vibe_event.is_set():
                            break
                        led_backend.set_rumble(power, power // 3)
                        time.sleep(0.04)
                    led_backend.set_rumble(0, 0)

                elif profile_type == "shield_impact":
                    dpg.configure_item("hud_vibe_status", default_value="KINETIC IMPACT WAVE", color=C_ALERT_RED)
                    # Triple staggered shockwave
                    shocks = [(255, 255, 0.08), (0, 0, 0.05), (180, 240, 0.12), (0, 0, 0.06), (255, 120, 0.15)]
                    for w, s, duration in shocks:
                        if _stop_vibe_event.is_set():
                            break
                        led_backend.set_rumble(w, s)
                        time.sleep(duration)
                    led_backend.set_rumble(0, 0)

                elif profile_type == "max_thrust":
                    dpg.configure_item("hud_vibe_status", default_value="FULL THRUST OVERLOAD (2.0s)", color=C_ALERT_RED)
                    led_backend.set_rumble(255, 255)
                    for _ in range(20):
                        if _stop_vibe_event.is_set():
                            break
                        time.sleep(0.1)
                    led_backend.set_rumble(0, 0)

                elif profile_type == "cutoff":
                    led_backend.set_rumble(0, 0)
                    dpg.set_value("rumble_weak", 0)
                    dpg.set_value("rumble_strong", 0)
                    dpg.set_value("meter_weak", 0.0)
                    dpg.set_value("meter_strong", 0.0)
                    dpg.configure_item("meter_weak", overlay="0%")
                    dpg.configure_item("meter_strong", overlay="0%")
                    dpg.configure_item("hud_vibe_status", default_value="ALL THRUSTERS STANDBY", color=C_TEXT_DIM)
                    return

            finally:
                led_backend.set_rumble(0, 0)
                if not _stop_vibe_event.is_set():
                    dpg.configure_item("hud_vibe_status", default_value="SYSTEM READY // STANDBY", color=C_WARP_GREEN)

        _vibe_thread = threading.Thread(target=_worker, daemon=True)
        _vibe_thread.start()

    # ── Manual Rumble Handler ─────────────────────────────────────────────────
    def on_manual_rumble_change(sender, app_data, user_data):
        rw = dpg.get_value("rumble_weak")
        rs = dpg.get_value("rumble_strong")
        dpg.set_value("meter_weak", rw / 255.0)
        dpg.set_value("meter_strong", rs / 255.0)
        dpg.configure_item("meter_weak", overlay=f"{int((rw/255)*100)}%")
        dpg.configure_item("meter_strong", overlay=f"{int((rs/255)*100)}%")
        dpg.configure_item("hud_vibe_status", default_value=f"MANUAL ENGAGE: GYRO={rw} SUBLIGHT={rs}", color=C_SOLAR_ORANGE)
        led_backend.set_rumble(rw, rs)

    # ── LED Reactor Core Handler ──────────────────────────────────────────────
    def on_reactor_slider_change(sender, app_data, user_data):
        r = dpg.get_value("core_r")
        g = dpg.get_value("core_g")
        b = dpg.get_value("core_b")
        update_core_preview(r, g, b)
        led_backend.set_color(r, g, b)

    def update_core_preview(r, g, b):
        # Update preview box & reactor core circle
        dpg.configure_item("reactor_preview_rect", fill=[r, g, b, 255])
        dpg.configure_item("reactor_circle_core", fill=[r, g, b, 240])
        dpg.configure_item("reactor_glow_ring", color=[min(255, r + 40), min(255, g + 40), min(255, b + 40), 200])
        hex_code = f"#{r:02X}{g:02X}{b:02X}"
        dpg.configure_item("txt_core_hex", default_value=f"EMISSION: {hex_code}")
        dpg.configure_item("txt_core_rgb", default_value=f"ION-R:{r:03d}  PLASMA-G:{g:03d}  HYPER-B:{b:03d}")

    def apply_reactor_preset(r, g, b, name):
        stop_pulse_mode()
        dpg.set_value("core_r", r)
        dpg.set_value("core_g", g)
        dpg.set_value("core_b", b)
        update_core_preview(r, g, b)
        led_backend.set_color(r, g, b)
        dpg.configure_item("hud_reactor_status", default_value=f"REACTOR ONLINE // {name}", color=C_WARP_GREEN if (r+g+b)>0 else C_TEXT_DIM)

    # ── Pulse Stasis Breath Mode ──────────────────────────────────────────────
    def toggle_pulse_mode(sender, app_data):
        global _pulse_active, _pulse_thread
        _pulse_active = app_data
        if _pulse_active:
            dpg.configure_item("hud_reactor_status", default_value="REACTOR STASIS PULSE ACTIVE", color=C_PLASMA_BLUE)
            def _pulse_loop():
                base_r = dpg.get_value("core_r") or 200
                base_g = dpg.get_value("core_g")
                base_b = dpg.get_value("core_b")
                step = 0
                while _pulse_active:
                    factor = (math.sin(step) + 1.0) / 2.0  # 0.0 to 1.0
                    cur_r = int(base_r * factor)
                    cur_g = int(base_g * factor)
                    cur_b = int(base_b * factor)
                    led_backend.set_color(cur_r, cur_g, cur_b)
                    if dpg.does_item_exist("reactor_circle_core"):
                        dpg.configure_item("reactor_circle_core", fill=[cur_r, cur_g, cur_b, 240])
                    step += 0.12
                    time.sleep(0.04)
                # Restore original
                led_backend.set_color(dpg.get_value("core_r"), dpg.get_value("core_g"), dpg.get_value("core_b"))
            _pulse_thread = threading.Thread(target=_pulse_loop, daemon=True)
            _pulse_thread.start()
        else:
            stop_pulse_mode()

    def stop_pulse_mode():
        global _pulse_active
        _pulse_active = False
        if dpg.does_item_exist("chk_pulse_mode"):
            dpg.set_value("chk_pulse_mode", False)

    # ── Window Definition ─────────────────────────────────────────────────────
    win_w = 1000 if standalone else 980
    win_h = 620 if standalone else 580
    win_pos = [10, 10] if standalone else [180, 130]

    with dpg.window(
        tag="led_window",
        label="STARSHIP SUBSYSTEM // WARP CORE & HAPTICS CONSOLE",
        show=standalone,
        width=win_w,
        height=win_h,
        pos=win_pos,
        no_collapse=True,
        no_close=standalone,
    ):
        # ── Cockpit Top Telemetry Bar ─────────────────────────────────────────
        with dpg.group(horizontal=True):
            dpg.add_text("⚡ STARSHIP TELEMETRY CONSOLE", color=C_ALERT_RED)
            dpg.add_spacer(width=20)
            dpg.add_text("INTERFACE:", color=C_TEXT_DIM)
            dpg.add_text("SEARCHING...", tag="led_status_txt", color=C_WARP_GREEN)
            dpg.add_spacer(width=20)
            dpg.add_text("CORE STATUS:", color=C_TEXT_DIM)
            dpg.add_text("ONLINE", tag="hud_reactor_status", color=C_WARP_GREEN)
            dpg.add_spacer(width=30)
            dpg.add_button(label="[ EMERGENCY CUTOFF ]", callback=lambda: run_vibration_profile("cutoff"))

        dpg.add_separator()
        dpg.add_spacer(height=6)

        # ── Cockpit Dual Flight Deck ──────────────────────────────────────────
        with dpg.group(horizontal=True):

            # ══════════════════════════════════════════════════════════════════
            # BAY 1: WARP CORE REACTOR (PS4 LIGHTBAR)
            # ══════════════════════════════════════════════════════════════════
            with dpg.child_window(tag="bay_reactor", width=465, height=500, border=True):
                dpg.add_text("REACTOR BAY // LIGHTBAR TELEMETRY", color=C_ALERT_RED)
                dpg.add_separator()
                dpg.add_spacer(height=4)

                # Reactor Output Gauges
                dpg.add_text("CORE EMISSION WAVELENGTHS", color=C_TEXT_DIM)
                dpg.add_slider_int(
                    label=" [ION RED]##r", tag="core_r",
                    min_value=0, max_value=255, default_value=200,
                    width=290, callback=on_reactor_slider_change
                )
                dpg.add_slider_int(
                    label=" [PLASMA GREEN]##g", tag="core_g",
                    min_value=0, max_value=255, default_value=0,
                    width=290, callback=on_reactor_slider_change
                )
                dpg.add_slider_int(
                    label=" [HYPER BLUE]##b", tag="core_b",
                    min_value=0, max_value=255, default_value=0,
                    width=290, callback=on_reactor_slider_change
                )

                dpg.add_spacer(height=6)

                # Visual Reactor Chamber Canvas
                with dpg.drawlist(tag="reactor_chamber_canvas", width=440, height=84):
                    # Outer containment bracket
                    dpg.draw_rectangle([0, 0], [440, 84], color=C_BORDER_NEON, fill=C_PANEL_BG, rounding=8)
                    # Glowing center core
                    dpg.draw_circle([50, 42], 30, color=[40, 10, 15, 255], fill=[20, 5, 8, 255])
                    dpg.draw_circle([50, 42], 24, color=C_ALERT_RED, fill=[200, 0, 0, 240], tag="reactor_circle_core")
                    dpg.draw_circle([50, 42], 30, color=C_ALERT_RED, tag="reactor_glow_ring")
                    # Reactor status text
                    dpg.draw_text([100, 20], "WARP CONTAINMENT CHAMBER // ALPHA", color=C_TEXT_DIM, size=11)
                    # Output preview strip
                    dpg.draw_rectangle([100, 42], [420, 68], fill=[200, 0, 0, 255], color=C_BORDER_NEON, rounding=4, tag="reactor_preview_rect")

                with dpg.group(horizontal=True):
                    dpg.add_text("EMISSION: #C80000", tag="txt_core_hex", color=C_TEXT_DIM)
                    dpg.add_spacer(width=20)
                    dpg.add_text("ION-R:200  PLASMA-G:000  HYPER-B:000", tag="txt_core_rgb", color=C_WHITE_HOT)

                dpg.add_spacer(height=8)
                dpg.add_text("TACTICAL EMISSION PRESETS", color=C_ALERT_RED)
                dpg.add_separator()
                dpg.add_spacer(height=3)

                # Tactical Presets (Large ergonomic buttons)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="[ RED ALERT ]", width=140, height=28,
                                   callback=lambda: apply_reactor_preset(255, 0, 0, "RED ALERT"))
                    dpg.add_button(label="[ PLASMA BLUE ]", width=140, height=28,
                                   callback=lambda: apply_reactor_preset(0, 130, 255, "PLASMA BLUE"))
                    dpg.add_button(label="[ WARP GREEN ]", width=140, height=28,
                                   callback=lambda: apply_reactor_preset(0, 255, 65, "WARP GREEN"))

                with dpg.group(horizontal=True):
                    dpg.add_button(label="[ SOLAR FLARE ]", width=140, height=28,
                                   callback=lambda: apply_reactor_preset(255, 140, 0, "SOLAR FLARE"))
                    dpg.add_button(label="[ CYBER VOID ]", width=140, height=28,
                                   callback=lambda: apply_reactor_preset(190, 0, 255, "CYBER VOID"))
                    dpg.add_button(label="[ HYPER WHITE ]", width=140, height=28,
                                   callback=lambda: apply_reactor_preset(255, 255, 255, "HYPERION WHITE"))

                with dpg.group(horizontal=True):
                    dpg.add_button(label="[ CLOAKING MODE (LED OFF) ]", width=290, height=28,
                                   callback=lambda: apply_reactor_preset(0, 0, 0, "CLOAKING ENGAGED"))

                dpg.add_spacer(height=10)
                dpg.add_text("REACTOR AUTOMATION MODES", color=C_ALERT_RED)
                dpg.add_separator()
                dpg.add_checkbox(
                    label=" Engage Stasis Pulse (Smooth Breathing Reactor)",
                    tag="chk_pulse_mode", callback=toggle_pulse_mode
                )

            dpg.add_spacer(width=10)

            # ══════════════════════════════════════════════════════════════════
            # BAY 2: PROPULSION & HAPTICS ENGINE (VIBRATION SUITE)
            # ══════════════════════════════════════════════════════════════════
            with dpg.child_window(tag="bay_haptics", width=465, height=500, border=True):
                dpg.add_text("PROPULSION BAY // HAPTIC FLIGHT ENGINES", color=C_ALERT_RED)
                dpg.add_separator()
                dpg.add_spacer(height=4)

                # Manual Dual-Thruster Sliders & Gauges
                dpg.add_text("MANUAL THRUSTER LEVEL OVERRIDE", color=C_TEXT_DIM)

                dpg.add_text("Stabilizer Gyros (Weak Motor / High Freq):", color=C_TEXT_DIM)
                dpg.add_slider_int(
                    label="##rw", tag="rumble_weak",
                    min_value=0, max_value=255, default_value=0,
                    width=300, callback=on_manual_rumble_change
                )
                dpg.add_progress_bar(tag="meter_weak", default_value=0.0, width=300, height=14, overlay="0%")

                dpg.add_spacer(height=4)
                dpg.add_text("Sublight Engines (Strong Motor / Deep Bass):", color=C_TEXT_DIM)
                dpg.add_slider_int(
                    label="##rs", tag="rumble_strong",
                    min_value=0, max_value=255, default_value=0,
                    width=300, callback=on_manual_rumble_change
                )
                dpg.add_progress_bar(tag="meter_strong", default_value=0.0, width=300, height=14, overlay="0%")

                dpg.add_spacer(height=6)
                with dpg.group(horizontal=True):
                    dpg.add_button(label="[ ENGAGE MANUAL THRUST ]", width=210, height=26,
                                   callback=lambda: led_backend.set_rumble(dpg.get_value("rumble_weak"), dpg.get_value("rumble_strong")))
                    dpg.add_button(label="[ DISENGAGE ]", width=120, height=26,
                                   callback=lambda: run_vibration_profile("cutoff"))

                dpg.add_spacer(height=10)
                dpg.add_text("AUTOMATED FLIGHT VIBRATION SUITE", color=C_ALERT_RED)
                dpg.add_separator()
                dpg.add_spacer(height=3)

                # 4 Main Flight Profiles
                with dpg.group(horizontal=True):
                    dpg.add_button(label="[ WARP PULSE ]\n180ms High-Freq Snap", width=210, height=44,
                                   callback=lambda: run_vibration_profile("warp_pulse"))
                    dpg.add_button(label="[ ENGINE RUMBLE ]\n1.2s Sublight Burn", width=210, height=44,
                                   callback=lambda: run_vibration_profile("engine_rumble"))

                with dpg.group(horizontal=True):
                    dpg.add_button(label="[ HYPERDRIVE SPOOL ]\nRamping Freq Sweep", width=210, height=44,
                                   callback=lambda: run_vibration_profile("hyperdrive_spool"))
                    dpg.add_button(label="[ SHIELD BREACH ]\nTriple Kinetic Shock", width=210, height=44,
                                   callback=lambda: run_vibration_profile("shield_impact"))

                with dpg.group(horizontal=True):
                    dpg.add_button(label="[ FULL THRUST OVERLOAD ]\nMax Dual Power Test", width=310, height=36,
                                   callback=lambda: run_vibration_profile("max_thrust"))
                    dpg.add_button(label="[ CUTOFF ]", width=110, height=36,
                                   callback=lambda: run_vibration_profile("cutoff"))

                dpg.add_spacer(height=10)
                dpg.add_separator()
                with dpg.group(horizontal=True):
                    dpg.add_text("PROPULSION STATUS:", color=C_TEXT_DIM)
                    dpg.add_text("SYSTEM READY // STANDBY", tag="hud_vibe_status", color=C_WARP_GREEN)

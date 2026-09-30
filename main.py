#!/usr/bin/env python3
"""
main.py — Controller Dashboard
Red & black Dear PyGui dashboard for PS4 / any gamepad.
Features a massive Virtual Controller layout and native Color Picker.
"""
import dearpygui.dearpygui as dpg
import time
import os
from collections import deque

from theme import apply_theme
from controller_reader import ControllerReader
from ps4_led import PS4LED
from led_ui import build_led_window

# ─── Constants ────────────────────────────────────────────────────────────────
VP_W, VP_H   = 1420, 940
HISTORY_LEN  = 300
CHART_H      = 170

# ── Colors ────────────────────────────────────────────────────────────────────
C_RED        = [200, 30,  30,  255]
C_RED_BRIGHT = [255, 60,  60,  255]
C_IDLE       = [30,  5,   5,   255]
C_PRESSED    = [220, 35,  35,  255]
C_BORDER     = [90,  15,  15,  255]
C_DIM        = [90,  90,  90,  255]
C_WHITE      = [220, 220, 220, 255]
C_BG_DARK    = [12,  3,   3,   255]
C_STICK_BG   = [22,  4,   4,   255]
C_STICK_RING = [45,  8,   8,   255]
C_GRID       = [40,  40,  40,  255]
C_GREEN_ON   = [30,  200, 30,  255]
C_GREEN_OFF  = [80,  20,  20,  255]
C_PAD        = [25,  6,   6,   255]

AXIS_NAMES = ["L-Stick X", "L-Stick Y", "R-Stick X", "R-Stick Y", "L2", "R2"]

# ─── Global state ─────────────────────────────────────────────────────────────
reader  = ControllerReader()
led     = PS4LED()
history = {i: deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN) for i in range(6)}
x_data  = list(range(HISTORY_LEN))

_frame_count   = 0
_fps_timer     = time.time()
_fps_display   = 0

# ─── Callbacks ────────────────────────────────────────────────────────────────

def on_dz_change(sender, app_data, user_data):
    reader.set_deadzone(user_data, app_data)

def on_sens_change(sender, app_data, user_data):
    reader.set_sensitivity(user_data, app_data)

# ─── UI Builder ───────────────────────────────────────────────────────────────

def build_ui():
    with dpg.window(
        tag="main_win",
        no_title_bar=True, no_move=True, no_resize=True,
        no_scrollbar=True, no_scroll_with_mouse=True,
        pos=[0, 0], width=VP_W, height=VP_H,
    ):
        _build_header()
        dpg.add_separator()
        dpg.add_spacer(height=10)

        with dpg.group(horizontal=True):
            _build_virtual_controller()
            dpg.add_spacer(width=20)
            _build_raw_data_panel()

        dpg.add_spacer(height=10)
        _build_axis_settings()
        _build_chart()

    # Build the popup LED window from the external file
    build_led_window(led)


# ── Header ────────────────────────────────────────────────────────────────────

def _build_header():
    with dpg.group(horizontal=True):
        dpg.add_text("  CONTROLLER DASHBOARD", color=C_RED)
        dpg.add_spacer(width=20)
        dpg.add_text("No controller", tag="hdr_name", color=C_DIM)
        dpg.add_spacer(width=20)
        dpg.add_text("● DISCONNECTED", tag="hdr_status", color=C_GREEN_OFF)
        dpg.add_spacer(width=20)
        dpg.add_text("BATTERY:", color=C_DIM)
        dpg.add_spacer(width=4)
        dpg.add_text("--", tag="hdr_batt", color=C_DIM)
        dpg.add_spacer(width=4)
        dpg.add_button(label="Refresh", width=60, callback=lambda: reader.force_battery_check())
        dpg.add_spacer(width=20)
        
        # New LED Control button
        dpg.add_button(label=" 💡 LED & RUMBLE CONTROLS ", callback=lambda: dpg.show_item("led_window"))
        dpg.add_spacer(width=40)
        
        dpg.add_text("FPS:", color=C_DIM)
        dpg.add_spacer(width=4)
        dpg.add_text("--", tag="hdr_fps", color=C_DIM)

# ── Virtual Controller ────────────────────────────────────────────────────────

def _build_virtual_controller():
    with dpg.child_window(tag="vc_panel", width=900, height=390, border=True):
        dpg.add_text("VIRTUAL CONTROLLER", color=C_RED)
        dpg.add_separator()
        
        with dpg.drawlist(tag="vc_canvas", width=880, height=340):
            CX, CY = 440, 170
            
            # Controller background silhouette
            dpg.draw_rectangle([CX - 320, CY - 130], [CX + 320, CY + 140], color=C_PAD, fill=C_PAD, rounding=80)
            dpg.draw_rectangle([CX - 150, CY - 50], [CX + 150, CY + 140], color=C_BG_DARK, fill=C_BG_DARK) # Cutout

            # ── Touchpad & Center Buttons ──
            dpg.draw_rectangle([CX - 80, CY - 120], [CX + 80, CY - 20], color=C_BORDER, fill=C_IDLE, rounding=10, tag="vc_touch")
            dpg.draw_text([CX - 30, CY - 75], "TOUCH", color=C_DIM, size=12)
            
            dpg.draw_circle([CX - 120, CY - 90], 8, color=C_BORDER, fill=C_IDLE, tag="vc_share")
            dpg.draw_text([CX - 145, CY - 110], "SHARE", color=C_DIM, size=10)
            
            dpg.draw_circle([CX + 120, CY - 90], 8, color=C_BORDER, fill=C_IDLE, tag="vc_options")
            dpg.draw_text([CX + 110, CY - 110], "OPTS", color=C_DIM, size=10)
            
            dpg.draw_circle([CX, CY + 20], 12, color=C_BORDER, fill=C_IDLE, tag="vc_ps")
            dpg.draw_text([CX - 8, CY + 13], "PS", color=C_DIM, size=10)

            # ── D-Pad (Left) ──
            DP_X, DP_Y = CX - 200, CY - 50
            dpg.draw_rectangle([DP_X - 12, DP_Y - 40], [DP_X + 12, DP_Y - 12], color=C_BORDER, fill=C_IDLE, rounding=2, tag="vc_du")
            dpg.draw_rectangle([DP_X - 12, DP_Y + 12], [DP_X + 12, DP_Y + 40], color=C_BORDER, fill=C_IDLE, rounding=2, tag="vc_dd")
            dpg.draw_rectangle([DP_X - 40, DP_Y - 12], [DP_X - 12, DP_Y + 12], color=C_BORDER, fill=C_IDLE, rounding=2, tag="vc_dl")
            dpg.draw_rectangle([DP_X + 12, DP_Y - 12], [DP_X + 40, DP_Y + 12], color=C_BORDER, fill=C_IDLE, rounding=2, tag="vc_dr")

            # ── Face Buttons (Right) ──
            FB_X, FB_Y = CX + 200, CY - 50
            dpg.draw_circle([FB_X, FB_Y - 30], 14, color=C_BORDER, fill=C_IDLE, tag="vc_tri")
            dpg.draw_text([FB_X - 5, FB_Y - 37], "T", color=C_WHITE, size=14) # Tri
            dpg.draw_circle([FB_X, FB_Y + 30], 14, color=C_BORDER, fill=C_IDLE, tag="vc_x")
            dpg.draw_text([FB_X - 5, FB_Y + 23], "X", color=C_WHITE, size=14) # X
            dpg.draw_circle([FB_X - 30, FB_Y], 14, color=C_BORDER, fill=C_IDLE, tag="vc_sq")
            dpg.draw_text([FB_X - 35, FB_Y - 7], "S", color=C_WHITE, size=14) # Sq
            dpg.draw_circle([FB_X + 30, FB_Y], 14, color=C_BORDER, fill=C_IDLE, tag="vc_o")
            dpg.draw_text([FB_X + 25, FB_Y - 7], "O", color=C_WHITE, size=14) # O

            # ── Sticks (Bottom Center) ──
            LS_X, LS_Y = CX - 100, CY + 60
            RS_X, RS_Y = CX + 100, CY + 60
            # L-Stick Base
            dpg.draw_circle([LS_X, LS_Y], 45, color=C_BORDER, fill=C_STICK_BG)
            dpg.draw_circle([LS_X, LS_Y], 45, color=C_IDLE, fill=[0,0,0,0], tag="vc_l3") # Ring highlight for L3
            dpg.draw_circle([LS_X, LS_Y], 15, color=C_RED_BRIGHT, fill=C_RED, tag="vc_lstick_dot")
            # R-Stick Base
            dpg.draw_circle([RS_X, RS_Y], 45, color=C_BORDER, fill=C_STICK_BG)
            dpg.draw_circle([RS_X, RS_Y], 45, color=C_IDLE, fill=[0,0,0,0], tag="vc_r3") # Ring highlight for R3
            dpg.draw_circle([RS_X, RS_Y], 15, color=C_RED_BRIGHT, fill=C_RED, tag="vc_rstick_dot")

            # ── Bumpers & Triggers (Top) ──
            L_TOP, R_TOP = CX - 200, CX + 200
            Y_BUMP = CY - 145
            dpg.draw_rectangle([L_TOP - 40, Y_BUMP], [L_TOP + 40, Y_BUMP + 15], color=C_BORDER, fill=C_IDLE, rounding=5, tag="vc_l1")
            dpg.draw_text([L_TOP - 8, Y_BUMP], "L1", color=C_WHITE, size=12)
            dpg.draw_rectangle([R_TOP - 40, Y_BUMP], [R_TOP + 40, Y_BUMP + 15], color=C_BORDER, fill=C_IDLE, rounding=5, tag="vc_r1")
            dpg.draw_text([R_TOP - 8, Y_BUMP], "R1", color=C_WHITE, size=12)

            # Triggers as dynamic filled rectangles growing upwards
            dpg.draw_rectangle([L_TOP - 40, Y_BUMP - 40], [L_TOP + 40, Y_BUMP - 5], color=C_BORDER, fill=C_STICK_BG, rounding=4)
            dpg.draw_rectangle([L_TOP - 40, Y_BUMP - 5], [L_TOP + 40, Y_BUMP - 5], color=[0,0,0,0], fill=C_RED, rounding=4, tag="vc_l2_fill")
            dpg.draw_text([L_TOP - 8, Y_BUMP - 25], "L2", color=C_WHITE, size=12)

            dpg.draw_rectangle([R_TOP - 40, Y_BUMP - 40], [R_TOP + 40, Y_BUMP - 5], color=C_BORDER, fill=C_STICK_BG, rounding=4)
            dpg.draw_rectangle([R_TOP - 40, Y_BUMP - 5], [R_TOP + 40, Y_BUMP - 5], color=[0,0,0,0], fill=C_RED, rounding=4, tag="vc_r2_fill")
            dpg.draw_text([R_TOP - 8, Y_BUMP - 25], "R2", color=C_WHITE, size=12)


def _build_raw_data_panel():
    with dpg.child_window(tag="raw_panel", width=480, height=390, border=True):
        dpg.add_text("RAW DATA", color=C_RED)
        dpg.add_separator()
        
        with dpg.group(horizontal=True):
            dpg.add_text("L-Stick:", color=C_DIM)
            dpg.add_text("X: 0.000  Y: 0.000", tag="txt_ls", color=C_WHITE)
        with dpg.group(horizontal=True):
            dpg.add_text("R-Stick:", color=C_DIM)
            dpg.add_text("X: 0.000  Y: 0.000", tag="txt_rs", color=C_WHITE)
        with dpg.group(horizontal=True):
            dpg.add_text("Triggers:", color=C_DIM)
            dpg.add_text("L2: 0.000  R2: 0.000", tag="txt_trig", color=C_WHITE)
        
        dpg.add_spacer(height=10)
        dpg.add_text("Axes List:", color=C_DIM)
        for i in range(6):
            with dpg.group(horizontal=True):
                dpg.add_text(f"  {AXIS_NAMES[i]:<12}", color=C_DIM)
                dpg.add_text("0.000", tag=f"raw_ax_{i}", color=C_WHITE)


# ── Axis settings ─────────────────────────────────────────────────────────────

def _build_axis_settings():
    with dpg.collapsing_header(label="   AXIS SETTINGS  —  Deadzone & Sensitivity"):
        dpg.add_spacer(height=4)
        cols = 3
        for i in range(6):
            if i % cols == 0:
                grp = dpg.add_group(horizontal=True)
                dpg.push_container_stack(grp)
            with dpg.group():
                dpg.add_text(f"Axis {i} — {AXIS_NAMES[i]}", color=C_DIM)
                dpg.add_slider_float(
                    label=f"Deadzone##dz{i}", tag=f"dz_{i}",
                    min_value=0.0, max_value=0.50, default_value=0.08,
                    width=200, format="%.3f",
                    callback=on_dz_change, user_data=i,
                )
                dpg.add_slider_float(
                    label=f"Sensitivity##s{i}", tag=f"sens_{i}",
                    min_value=0.10, max_value=3.0, default_value=1.0,
                    width=200, format="%.2f",
                    callback=on_sens_change, user_data=i,
                )
                dpg.add_spacer(width=30)
            if i % cols == cols - 1 or i == 5:
                dpg.pop_container_stack()
        dpg.add_spacer(height=4)

# ── Live chart ────────────────────────────────────────────────────────────────

def _build_chart():
    with dpg.collapsing_header(label="   LIVE AXIS CHART", default_open=False):
        dpg.add_spacer(height=4)
        with dpg.group(horizontal=True):
            dpg.add_text("Show:", color=C_DIM)
            for i, name in enumerate(AXIS_NAMES):
                dpg.add_spacer(width=10)
                dpg.add_checkbox(label=name, tag=f"chart_show_{i}",
                                 default_value=(i in (0, 2)))
        dpg.add_spacer(height=4)

        with dpg.plot(tag="axis_plot", height=CHART_H, width=-1, no_menus=False):
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, tag="plot_x",
                              no_tick_labels=True, no_gridlines=True)
            dpg.set_axis_limits("plot_x", 0, HISTORY_LEN)

            y_ax = dpg.add_plot_axis(dpg.mvYAxis, tag="plot_y")
            dpg.set_axis_limits("plot_y", -1.15, 1.15)

            colors = [
                [220, 30,  30,  200], [220, 100, 30,  200],
                [30,  150, 220, 200], [30,  220, 150, 200],
                [220, 30,  180, 200], [200, 200, 30,  200],
            ]
            for i, name in enumerate(AXIS_NAMES):
                dpg.add_line_series(x_data, list(history[i]), label=name, tag=f"series_{i}", parent=y_ax)
                with dpg.theme() as s_theme:
                    with dpg.theme_component(dpg.mvLineSeries):
                        dpg.add_theme_color(dpg.mvPlotCol_Line, colors[i], category=dpg.mvThemeCat_Plots)
                dpg.bind_item_theme(f"series_{i}", s_theme)


# ─── Frame update ─────────────────────────────────────────────────────────────

def update_frame():
    global _frame_count, _fps_timer, _fps_display

    state = reader.get_state()

    # ── FPS ──
    _frame_count += 1
    now = time.time()
    if now - _fps_timer >= 1.0:
        _fps_display = _frame_count
        _frame_count = 0
        _fps_timer   = now
    dpg.configure_item("hdr_fps", default_value=str(_fps_display))

    # ── Connection status ──
    if state["connected"]:
        dpg.configure_item("hdr_name",   default_value=state["name"])
        dpg.configure_item("hdr_status", default_value="● CONNECTED", color=C_GREEN_ON)
        
        batt_pct = state.get("battery_pct")
        if batt_pct is not None:
            batt_stat = state.get("battery_status", "")
            dpg.configure_item("hdr_batt", default_value=f"{batt_pct}% ({batt_stat})", color=C_WHITE)
        else:
            dpg.configure_item("hdr_batt", default_value="Unknown", color=C_DIM)
    else:
        dpg.configure_item("hdr_name",   default_value="No controller")
        dpg.configure_item("hdr_status", default_value="● DISCONNECTED", color=C_GREEN_OFF)
        dpg.configure_item("hdr_batt",   default_value="--", color=C_DIM)
        return

    axes    = state["axes"]
    raw     = state["axes_raw"]
    buttons = state["buttons"]
    hats    = state["hats"]

    # ── Virtual Controller Update ──
    
    # Face & Bumpers & Center mapping
    # 0:X, 1:O, 2:Tri, 3:Sq, 4:L1, 5:R1, 8:Share, 9:Options, 10/12:PS, 13:Touch, 11:L3, 12:R3
    v_map = {
        0: "vc_x", 1: "vc_o", 2: "vc_tri", 3: "vc_sq",
        4: "vc_l1", 5: "vc_r1",
        8: "vc_share", 9: "vc_options", 10: "vc_l3", 11: "vc_r3",
        12: "vc_ps", 13: "vc_touch"
    }
    for i in range(len(buttons)):
        if i in v_map:
            fill = C_PRESSED if buttons[i] else C_IDLE
            color = C_RED if buttons[i] else C_BORDER
            dpg.configure_item(v_map[i], fill=fill)
            # Make sticks ring glow on L3/R3
            if i == 10 or i == 11: # usually L3 / R3
                ring_tag = "vc_l3" if i == 10 else "vc_r3"
                pass 

    if len(buttons) > 11 and buttons[11]: dpg.configure_item("vc_l3", color=C_RED, thickness=2)
    else: dpg.configure_item("vc_l3", color=C_IDLE, thickness=1)
    
    if len(buttons) > 12 and buttons[12]: dpg.configure_item("vc_r3", color=C_RED, thickness=2)
    else: dpg.configure_item("vc_r3", color=C_IDLE, thickness=1)

    # D-pad
    if hats:
        hx, hy = hats[0]
        dpg.configure_item("vc_du", fill=C_PRESSED if hy > 0 else C_IDLE)
        dpg.configure_item("vc_dd", fill=C_PRESSED if hy < 0 else C_IDLE)
        dpg.configure_item("vc_dl", fill=C_PRESSED if hx < 0 else C_IDLE)
        dpg.configure_item("vc_dr", fill=C_PRESSED if hx > 0 else C_IDLE)

    # Sticks
    CX, CY = 440, 170
    LS_X, LS_Y = CX - 100, CY + 60
    RS_X, RS_Y = CX + 100, CY + 60
    if len(axes) >= 2:
        lx, ly = axes[0], axes[1]
        dpg.configure_item("vc_lstick_dot", center=[LS_X + lx * 30, LS_Y + ly * 30])
        dpg.configure_item("txt_ls", default_value=f"X: {lx:+.3f}  Y: {ly:+.3f}")
    if len(axes) >= 4:
        rx, ry = axes[2], axes[3]
        dpg.configure_item("vc_rstick_dot", center=[RS_X + rx * 30, RS_Y + ry * 30])
        dpg.configure_item("txt_rs", default_value=f"X: {rx:+.3f}  Y: {ry:+.3f}")

    # Triggers (L2 = axes 4, R2 = axes 5)
    L_TOP, R_TOP, Y_BUMP = CX - 200, CX + 200, CY - 145
    if len(axes) >= 6:
        l2 = (axes[4] + 1.0) / 2.0
        r2 = (axes[5] + 1.0) / 2.0
        dpg.configure_item("vc_l2_fill", pmin=[L_TOP - 40, Y_BUMP - 5 - (35 * l2)])
        dpg.configure_item("vc_r2_fill", pmin=[R_TOP - 40, Y_BUMP - 5 - (35 * r2)])
        dpg.configure_item("txt_trig", default_value=f"L2: {l2:.3f}  R2: {r2:.3f}")

    # Raw axes
    for i in range(min(len(raw), 6)):
        dpg.configure_item(f"raw_ax_{i}", default_value=f"{raw[i]:+.4f}")

    # History
    for i in range(min(len(axes), 6)):
        history[i].append(axes[i])
        if dpg.get_value(f"chart_show_{i}"):
            dpg.set_value(f"series_{i}", [x_data, list(history[i])])
        else:
            dpg.set_value(f"series_{i}", [[], []])

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    dpg.create_context()
    apply_theme()

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if os.path.exists(font_path):
        with dpg.font_registry():
            fnt = dpg.add_font(font_path, 14)
        dpg.bind_font(fnt)

    build_ui()

    dpg.create_viewport(title="Controller Dashboard", width=VP_W, height=VP_H, resizable=False, min_width=VP_W, min_height=VP_H)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    reader.start()

    if led.connect():
        # Will update the secondary window's status text
        if dpg.does_item_exist("led_status_txt"):
            dpg.configure_item("led_status_txt", default_value=f"Connected ({led._mode})", color=[30, 200, 30, 255])
        led.set_color(200, 0, 0)
    else:
        if dpg.does_item_exist("led_status_txt"):
            dpg.configure_item("led_status_txt", default_value="Not found (Using fallback)", color=[200, 120, 30, 255])

    while dpg.is_dearpygui_running():
        update_frame()
        dpg.render_dearpygui_frame()

    reader.stop()
    led.close()
    dpg.destroy_context()

if __name__ == "__main__":
    main()

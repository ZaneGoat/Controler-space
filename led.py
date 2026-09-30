#!/usr/bin/env python3
"""
led.py — Standalone Starship Subsystem Console & Haptics Engine Launcher.
Can be executed directly via:
    python3 led.py
or accessed inside main.py via the header button.
"""
import dearpygui.dearpygui as dpg
from ps4_led import PS4LED
from theme import apply_theme
from led_ui import build_led_window


def main():
    dpg.create_context()
    apply_theme()

    led = PS4LED()
    connected = led.connect()

    dpg.create_viewport(
        title="STARSHIP SUBSYSTEM CONSOLE // WARP CORE & HAPTICS ENGINE",
        width=1020,
        height=660,
        resizable=False,
    )

    build_led_window(led, standalone=True)
    dpg.setup_dearpygui()
    dpg.show_viewport()

    if connected:
        if dpg.does_item_exist("led_status_txt"):
            dpg.configure_item("led_status_txt", default_value=f"CONNECTED ({led._mode})", color=[40, 255, 120, 255])
        led.set_color(200, 0, 0)
    else:
        if dpg.does_item_exist("led_status_txt"):
            dpg.configure_item("led_status_txt", default_value="DEVICE NOT DETECTED", color=[235, 35, 45, 255])

    while dpg.is_dearpygui_running():
        dpg.render_dearpygui_frame()

    led.close()
    dpg.destroy_context()


if __name__ == "__main__":
    main()

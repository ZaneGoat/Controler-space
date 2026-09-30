"""
theme.py — Deep red & black Dear PyGui theme for Controller Dashboard.
"""
import dearpygui.dearpygui as dpg

# ─── Color palette ────────────────────────────────────────────────────────────
RED          = (200, 30, 30, 255)
RED_HOVER    = (230, 50, 50, 255)
RED_ACTIVE   = (255, 70, 70, 255)
DARK_BG      = (8,   8,  8, 255)
PANEL_BG     = (16, 16, 16, 255)
DEEP_BG      = (5,   5,  5, 255)
BORDER       = (70, 10, 10, 255)
FRAME_BG     = (25,  4,  4, 255)
FRAME_HOV    = (40,  8,  8, 255)
TEXT         = (225, 225, 225, 255)
DIM_TEXT     = (100, 100, 100, 255)
SCROLLBAR    = (40,  5,  5, 255)
HEADER       = (50,  8,  8, 255)


def apply_theme():
    """Apply the red/black global theme."""
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Backgrounds
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg,         DARK_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg,          PANEL_BG)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg,          PANEL_BG)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg,          FRAME_BG)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered,   FRAME_HOV)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive,    (55, 10, 10, 255))

            # Borders
            dpg.add_theme_color(dpg.mvThemeCol_Border,           BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_BorderShadow,     (0, 0, 0, 0))

            # Buttons
            dpg.add_theme_color(dpg.mvThemeCol_Button,           RED)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,    RED_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,     RED_ACTIVE)

            # Sliders
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab,       RED)
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, RED_ACTIVE)

            # Check/radio
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark,        RED)

            # Headers (collapsing)
            dpg.add_theme_color(dpg.mvThemeCol_Header,           HEADER)
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered,    (70, 12, 12, 255))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive,     RED)

            # Titles
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg,          DEEP_BG)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive,    (40, 6, 6, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, DEEP_BG)

            # Tabs
            dpg.add_theme_color(dpg.mvThemeCol_Tab,              (25, 4, 4, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered,       RED_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive,        RED)

            # Scrollbars
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg,      DEEP_BG)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab,    SCROLLBAR)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabHovered, RED)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrabActive,  RED_ACTIVE)

            # Text
            dpg.add_theme_color(dpg.mvThemeCol_Text,             TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_TextDisabled,     DIM_TEXT)

            # Plot colors
            dpg.add_theme_color(dpg.mvThemeCol_PlotLines,        RED)
            dpg.add_theme_color(dpg.mvThemeCol_PlotLinesHovered, RED_HOVER)
            dpg.add_theme_color(dpg.mvThemeCol_PlotHistogram,    RED)

            # Separators
            dpg.add_theme_color(dpg.mvThemeCol_Separator,        BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorHovered, RED)
            dpg.add_theme_color(dpg.mvThemeCol_SeparatorActive,  RED_ACTIVE)

            # Rounding / padding
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,   6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,    4)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding,     4)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding,      4)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding,    4)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding,    4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding,    10, 10)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding,     6,  4)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,      8,  4)

    dpg.bind_theme(global_theme)

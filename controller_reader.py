"""
controller_reader.py — Universal gamepad reader via pygame.
Runs in a background thread. Thread-safe state dict for the UI.
Works with PS4, Xbox, Switch Pro, and any SDL-compatible controller.
"""
import pygame
import threading
import time
import os
import glob
import struct


class ControllerReader:
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._joystick = None

        self._touch_fd = None
        self._touch_active = False
        self._touch_x = 0.5
        self._touch_y = 0.5

        self.state = {
            "connected":   False,
            "name":        "No controller",
            "num_axes":    0,
            "num_buttons": 0,
            "num_hats":    0,
            "axes":        [],      # float -1.0 .. +1.0 (after deadzone/sens)
            "axes_raw":    [],      # raw float before processing
            "buttons":     [],      # list of bool
            "hats":        [],      # list of (int, int)
            "deadzones":   {},      # axis_idx -> float (0.0-0.5)
            "sensitivity": {},      # axis_idx -> float (0.1-3.0)
            "battery_pct": None,    # int 0-100 or None
            "battery_status": None, # str or None
            "touch_active": False,  # True if finger touching or clicked
            "touch_pos":   (0.5, 0.5), # normalized (0.0 to 1.0) (x, y)
        }
        self._wants_batt_check = True  # Check once on startup

    # ── Public API ────────────────────────────────────────────────────────────

    def force_battery_check(self):
        with self._lock:
            self._wants_batt_check = True

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def set_deadzone(self, axis: int, value: float):
        with self._lock:
            self.state["deadzones"][axis] = float(value)

    def set_sensitivity(self, axis: int, value: float):
        with self._lock:
            self.state["sensitivity"][axis] = float(value)

    def get_state(self) -> dict:
        with self._lock:
            return {
                "connected":   self.state["connected"],
                "name":        self.state["name"],
                "num_axes":    self.state["num_axes"],
                "num_buttons": self.state["num_buttons"],
                "num_hats":    self.state["num_hats"],
                "axes":        list(self.state["axes"]),
                "axes_raw":    list(self.state["axes_raw"]),
                "buttons":     list(self.state["buttons"]),
                "hats":        list(self.state["hats"]),
                "battery_pct": self.state["battery_pct"],
                "battery_status": self.state["battery_status"],
                "touch_active": self.state["touch_active"],
                "touch_pos":    self.state["touch_pos"],
            }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _init_touchpad(self):
        try:
            for event_path in glob.glob("/sys/class/input/event*"):
                name_file = os.path.join(event_path, "device", "name")
                if os.path.exists(name_file):
                    with open(name_file) as f:
                        name = f.read().lower()
                    if "touchpad" in name and ("wireless controller" in name or "dualshock" in name):
                        dev_node = os.path.join("/dev/input", os.path.basename(event_path))
                        if os.path.exists(dev_node):
                            self._touch_fd = os.open(dev_node, os.O_RDONLY | os.O_NONBLOCK)
                            return
        except Exception:
            self._touch_fd = None

    def _poll_touchpad(self):
        if self._touch_fd is None:
            self._init_touchpad()
        if self._touch_fd is not None:
            try:
                while True:
                    data = os.read(self._touch_fd, 24)
                    if len(data) < 24:
                        break
                    sec, usec, ev_type, ev_code, ev_val = struct.unpack("qqHHi", data)
                    if ev_type == 1 and ev_code == 330:  # BTN_TOUCH
                        self._touch_active = bool(ev_val)
                    elif ev_type == 3:  # EV_ABS
                        if ev_code == 53:  # ABS_MT_POSITION_X (0-1920)
                            self._touch_x = max(0.0, min(1.0, ev_val / 1920.0))
                        elif ev_code == 54:  # ABS_MT_POSITION_Y (0-942)
                            self._touch_y = max(0.0, min(1.0, ev_val / 942.0))
            except (BlockingIOError, OSError):
                pass

    def _read_battery(self):
        try:
            # Look for sysfs power_supply matching controller/gamepad patterns
            batteries = glob.glob("/sys/class/power_supply/*controller-battery*") + \
                        glob.glob("/sys/class/power_supply/*joystick*") + \
                        glob.glob("/sys/class/power_supply/*gamepad*")
            if not batteries:
                return None, None
            
            bat = batteries[0]
            with open(os.path.join(bat, "capacity"), "r") as f:
                cap = int(f.read().strip())
            with open(os.path.join(bat, "status"), "r") as f:
                stat = f.read().strip()
            return cap, stat
        except Exception:
            return None, None

    def _apply(self, raw: float, axis: int) -> float:
        """Apply deadzone and sensitivity to a raw axis value."""
        dz   = self.state["deadzones"].get(axis, 0.08)
        sens = self.state["sensitivity"].get(axis, 1.0)
        if abs(raw) < dz:
            return 0.0
        sign = 1.0 if raw > 0 else -1.0
        scaled = sign * ((abs(raw) - dz) / (1.0 - dz))
        return max(-1.0, min(1.0, scaled * sens))

    def _run(self):
        pygame.init()
        pygame.joystick.init()

        while self._running:
            pygame.event.pump()

            count = pygame.joystick.get_count()

            if count == 0:
                if self.state["connected"]:
                    with self._lock:
                        self.state["connected"] = False
                        self.state["name"]      = "No controller"
                if self._joystick:
                    try:
                        self._joystick.quit()
                    except Exception:
                        pass
                    self._joystick = None
                pygame.time.wait(500)
                continue

            # (Re)init joystick on first detection
            if self._joystick is None:
                try:
                    self._joystick = pygame.joystick.Joystick(0)
                    self._joystick.init()
                    n_a = self._joystick.get_numaxes()
                    n_b = self._joystick.get_numbuttons()
                    n_h = self._joystick.get_numhats()
                    with self._lock:
                        self.state["name"]        = self._joystick.get_name()
                        self.state["connected"]   = True
                        self.state["num_axes"]    = n_a
                        self.state["num_buttons"] = n_b
                        self.state["num_hats"]    = n_h
                        self.state["axes"]        = [0.0] * n_a
                        self.state["axes_raw"]    = [0.0] * n_a
                        self.state["buttons"]     = [False] * n_b
                        self.state["hats"]        = [(0, 0)] * n_h
                except Exception as e:
                    print(f"[ControllerReader] init error: {e}")
                    self._joystick = None
                    pygame.time.wait(500)
                    continue

            # Read values
            try:
                n_a = self._joystick.get_numaxes()
                n_b = self._joystick.get_numbuttons()
                n_h = self._joystick.get_numhats()

                raw_axes = [self._joystick.get_axis(i) for i in range(n_a)]
                proc_axes = [self._apply(raw_axes[i], i) for i in range(n_a)]
                buttons  = [bool(self._joystick.get_button(i)) for i in range(n_b)]
                hats     = [self._joystick.get_hat(i) for i in range(n_h)]
                
                # Check battery only when requested
                check_now = False
                with self._lock:
                    if getattr(self, '_wants_batt_check', False):
                        check_now = True
                        self._wants_batt_check = False
                
                if check_now:
                    pct, stat = self._read_battery()
                    with self._lock:
                        self.state["battery_pct"] = pct
                        self.state["battery_status"] = stat

                # Poll Touchpad
                self._poll_touchpad()
                is_touched = self._touch_active or (len(buttons) > 11 and buttons[11])

                with self._lock:
                    self.state["axes"]         = proc_axes
                    self.state["axes_raw"]     = raw_axes
                    self.state["buttons"]      = buttons
                    self.state["hats"]         = hats
                    self.state["touch_active"] = is_touched
                    self.state["touch_pos"]    = (self._touch_x, self._touch_y)

            except Exception as e:
                print(f"[ControllerReader] read error: {e}")
                try:
                    self._joystick.quit()
                except Exception:
                    pass
                self._joystick = None
                if self._touch_fd is not None:
                    try:
                        os.close(self._touch_fd)
                    except Exception:
                        pass
                    self._touch_fd = None
                with self._lock:
                    self.state["connected"] = False

            pygame.time.wait(1)   # ~1000 Hz for minimal latency

        pygame.joystick.quit()
        pygame.quit()

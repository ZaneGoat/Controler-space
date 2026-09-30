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


class ControllerReader:
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._joystick = None

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
            }

    # ── Internal ──────────────────────────────────────────────────────────────

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

                with self._lock:
                    self.state["axes"]     = proc_axes
                    self.state["axes_raw"] = raw_axes
                    self.state["buttons"]  = buttons
                    self.state["hats"]     = hats

            except Exception as e:
                print(f"[ControllerReader] read error: {e}")
                try:
                    self._joystick.quit()
                except Exception:
                    pass
                self._joystick = None
                with self._lock:
                    self.state["connected"] = False

            pygame.time.wait(1)   # ~1000 Hz for minimal latency

        pygame.joystick.quit()
        pygame.quit()

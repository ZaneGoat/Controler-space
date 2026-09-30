"""
ps4_led.py — PS4 DualShock 4 LED lightbar + rumble control.

Priority:
  1. sysfs LED interface  (via Linux 'playstation' kernel driver — cleanest)
  2. hidraw direct write  (raw HID report with CRC32 for BT)

Falls back gracefully if DS4 is not present.
"""
import os
import glob
import struct
import zlib
import subprocess
import threading


class PS4LED:
    def __init__(self):
        self._lock   = threading.Lock()
        self.available = False
        self._mode   = None   # "sysfs" | "hidraw" | None

        # sysfs paths
        self._led_red    = None
        self._led_green  = None
        self._led_blue   = None
        self._rumble_weak   = None
        self._rumble_strong = None

        # hidraw path (fallback)
        self._hidraw_path = None

        # Current state
        self._r, self._g, self._b = 200, 0, 0
        self._rw, self._rs = 0, 0   # rumble weak/strong

    # ── Discovery ─────────────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Discover DS4 LED interface. Returns True if found."""
        if self._try_sysfs():
            self.available = True
            self._mode = "sysfs"
            print("[PS4LED] Using sysfs LED interface")
            return True
        if self._try_hidraw():
            self.available = True
            self._mode = "hidraw"
            print(f"[PS4LED] Using hidraw at {self._hidraw_path}")
            return True
        print("[PS4LED] DS4 not found — LED control unavailable")
        self.available = False
        return False

    def _try_sysfs(self) -> bool:
        """Scan /sys/class/leds/ for DS4 RGB entries."""
        leds = glob.glob("/sys/class/leds/*")
        r_path = g_path = b_path = None
        rw_path = rs_path = None

        # The 'playstation' driver names them: input41:red  input41:green  etc.
        # We look for Sony DS4 device by checking the 'device' symlink vendor.
        ds4_prefixes = set()
        for led_path in leds:
            name = os.path.basename(led_path)
            # Check vendor via uevent
            uevent = os.path.join(led_path, "device", "uevent")
            try:
                with open(uevent) as f:
                    content = f.read().lower()
                if "054c" in content:  # Sony vendor
                    ds4_prefixes.add(name.rsplit(":", 1)[0])
            except Exception:
                pass

        for led_path in leds:
            name = os.path.basename(led_path)
            prefix = name.rsplit(":", 1)[0] if ":" in name else ""
            suffix = name.rsplit(":", 1)[-1] if ":" in name else ""

            # Accept if prefix matched Sony device OR it's a known input device
            is_candidate = (prefix in ds4_prefixes) or (
                "054c" in name.lower()
            )

            # Fallback: just pick up input4x:red/green/blue that appeared after BT connect
            if not is_candidate:
                # The PS4 created input41 on your system. Check dynamically.
                try:
                    devlink = os.path.join(led_path, "device")
                    realdev = os.path.realpath(devlink)
                    if "054c" in realdev.lower():
                        is_candidate = True
                except Exception:
                    pass

            # Last resort: grab input*:red/green/blue if no sysfs vendor check works
            # We'll grab first set that has all three colors
            if not is_candidate:
                continue

            if suffix == "red":
                r_path = os.path.join(led_path, "brightness")
            elif suffix == "green":
                g_path = os.path.join(led_path, "brightness")
            elif suffix == "blue":
                b_path = os.path.join(led_path, "brightness")
            elif "rumble" in suffix and "weak" in suffix:
                rw_path = os.path.join(led_path, "brightness")
            elif "rumble" in suffix and ("strong" in suffix or "left" in suffix):
                rs_path = os.path.join(led_path, "brightness")

        if r_path and g_path and b_path:
            if os.access(r_path, os.W_OK) and os.access(g_path, os.W_OK):
                self._led_red    = r_path
                self._led_green  = g_path
                self._led_blue   = b_path
                self._rumble_weak   = rw_path
                self._rumble_strong = rs_path
                return True

        # Second pass: try heuristic — grab input4x:red/green/blue where x>39
        # (DS4 usually registers as input40+ after keyboard/mouse)
        r_path = g_path = b_path = None
        for led_path in leds:
            name = os.path.basename(led_path)
            if ":" not in name:
                continue
            prefix, suffix = name.rsplit(":", 1)
            # e.g. "input41" — number >= 40 suggests a gamepad
            try:
                num = int("".join(c for c in prefix if c.isdigit()))
                if num < 40:
                    continue
            except ValueError:
                continue
            if suffix == "red":
                r_path = os.path.join(led_path, "brightness")
            elif suffix == "green":
                g_path = os.path.join(led_path, "brightness")
            elif suffix == "blue":
                b_path = os.path.join(led_path, "brightness")
            elif "rumble" in suffix:
                if "weak" in suffix:
                    rw_path = os.path.join(led_path, "brightness")
                else:
                    rs_path = os.path.join(led_path, "brightness")

        if r_path and g_path and b_path:
            # Check if we actually have permission to write to them!
            if os.access(r_path, os.W_OK) and os.access(g_path, os.W_OK):
                self._led_red    = r_path
                self._led_green  = g_path
                self._led_blue   = b_path
                self._rumble_weak   = rw_path
                self._rumble_strong = rs_path
                return True

        return False

    def _try_hidraw(self) -> bool:
        """Find DS4 hidraw node via udevadm info."""
        for i in range(15):
            path = f"/dev/hidraw{i}"
            if not os.path.exists(path):
                continue
            try:
                res = subprocess.run(
                    ["udevadm", "info", "--query=all", path],
                    capture_output=True, text=True, timeout=2
                )
                info = res.stdout.lower()
                if "054c" in info and ("09cc" in info or "05c4" in info):
                    self._hidraw_path = path
                    return True
            except Exception:
                continue
        return False

    # ── Public API ────────────────────────────────────────────────────────────

    def set_color(self, r: int, g: int, b: int):
        with self._lock:
            self._r, self._g, self._b = int(r), int(g), int(b)
        self._send()

    def set_rumble(self, weak: int, strong: int):
        with self._lock:
            self._rw, self._rs = int(weak), int(strong)
        self._send()

    def get_led_paths(self) -> dict:
        """Return sysfs LED paths for display in UI."""
        return {
            "red":    self._led_red,
            "green":  self._led_green,
            "blue":   self._led_blue,
            "mode":   self._mode,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _sysfs_write(self, path: str, value: int):
        try:
            with open(path, "w") as f:
                f.write(str(max(0, min(255, value))))
        except Exception as e:
            pass

    def _send(self):
        if not self.available:
            return
        with self._lock:
            r, g, b = self._r, self._g, self._b
            rw, rs  = self._rw, self._rs

        if self._mode == "sysfs":
            self._sysfs_write(self._led_red,   r)
            self._sysfs_write(self._led_green, g)
            self._sysfs_write(self._led_blue,  b)
            if self._rumble_weak:
                self._sysfs_write(self._rumble_weak, rw)
            if self._rumble_strong:
                self._sysfs_write(self._rumble_strong, rs)

        elif self._mode == "hidraw":
            self._send_hidraw(r, g, b, rw, rs)

    def _send_hidraw(self, r: int, g: int, b: int, rw: int, rs: int):
        """
        DS4 Bluetooth output report 0x11 — 79 bytes + CRC32.
        CRC is over:  [0xA2] + report[0..74]  (BT header + report body).
        """
        try:
            report = bytearray(79)
            report[0]  = 0x11   # Report ID
            report[1]  = 0xC0   # BT flags
            report[2]  = 0x20
            report[3]  = 0xF3   # Enable LED + rumble
            report[4]  = 0x04
            report[5]  = 0x00
            report[6]  = rw & 0xFF    # Rumble weak  (right / small)
            report[7]  = rs & 0xFF    # Rumble strong (left / big)
            report[8]  = r & 0xFF     # LED R
            report[9]  = g & 0xFF     # LED G
            report[10] = b & 0xFF     # LED B
            # Bytes 11..74 = 0x00 (flash timing, audio, etc.)

            # CRC32 over BT packet header + report body
            crc_input = bytes([0xA2]) + bytes(report[:75])
            crc = zlib.crc32(crc_input) & 0xFFFFFFFF
            struct.pack_into("<I", report, 75, crc)

            with open(self._hidraw_path, "wb") as f:
                f.write(bytes(report))

        except Exception as e:
            print(f"[PS4LED] hidraw write error: {e}")

    def close(self):
        """Stop rumble on exit."""
        if self.available:
            try:
                self.set_rumble(0, 0)
            except Exception:
                pass

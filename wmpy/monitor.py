"""Contains the Monitor class to track physical monitors"""
import win32api

from win32con import MONITOR_DEFAULTTOPRIMARY
from win32con import MONITOR_DEFAULTTONEAREST

from wmpy.window import Window

class Monitor(object):
    """Maps to a physical monitor"""

    def __init__(self, handle):
        self.handle = handle

    def __eq__(self, other):
        return int(self.handle) == int(other.handle)

    def __hash__(self):
        return hash(self.handle)

    def __str__(self):
        left, top, right, bottom = self.display_size
        return "{width}x{height} @ ({left}, {top}) [{handle}]{main}".format(
            handle=int(self.handle),
            left=left,
            top=top,
            width=right - left,
            height=bottom - top,
            main=" [PRIMARY]" if self.is_main() else ""
        )

    def is_main(self):
        """Returns True if this is the primary monitor"""
        try:
            if self.handle == win32api.MonitorFromPoint((0, 0), MONITOR_DEFAULTTOPRIMARY):
                return True
            else:
                return False
        except win32api.error:
            print("Error while grabbing the monitor with point (0, 0)")
            return None

    def contains_window(self, window):
        """Returns True is the window is in this monitor"""
        try:
            if win32api.MonitorFromWindow(window.handle, MONITOR_DEFAULTTONEAREST) == self.handle:
                return True
            else:
                return False
        except win32api.error:
            print("Error grabbing nearest monitor from window")
            return None

    def get_window_positions(self):
        """Returns a dictionary of Window: display size"""
        positions = {}
        for window in Window.get_windows_from_monitor(self):
            positions[window] = window.display_size
        return positions

    @property
    def display_size(self):
        """Returns the display size of this monitor"""
        try:
            return win32api.GetMonitorInfo(self.handle)["Work"]
        except win32api.error:
            print("error while grabbing monitor work area")
            return None

    @property
    def display_resolution(self):
        try:
            return win32api.GetMonitorInfo(self.handle)["Monitor"]
        except win32api.error:
            print("error while grabbing monitor display resolution")
            return None

    @staticmethod
    def get_displays():
        """Returns all physical monitors"""
        monitors = []
        try:
            for handle, _, _ in win32api.EnumDisplayMonitors():
                monitors.append(Monitor(handle))
            return monitors
        except win32api.error:
            print("Error while enumerating display monitors")
            return None

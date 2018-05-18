"""Contains Tiler class for managing window placement"""
import re
import win32gui
import win32api

from win32con import MOUSEEVENTF_LEFTUP
from win32con import MOUSEEVENTF_ABSOLUTE

import wmpy.config as config

# return True if two display_size overlap
def check_overlap(a, b):
    if a[0] >= b[2] or a[1] >= b[3] or a[2] <= b[0] or a[3] <= b[1]:
        return False
    return True

# return area of overlap between two display_size
def overlap_area(a, b):
    return min(a[2] - b[0], b[2] - a[0]) * min(a[3] - b[1], b[3] - a[1])

def add_margin(region, margin):
    return tuple(map(lambda x, y: x + y, region, margin))

class Tiler(object):
    """Manages a BSP tree for all windows in a monitor"""

    def __init__(self, monitor):
        self.monitor = monitor
        self.start_positions = monitor.get_window_positions()
        self.root = None
        self.windows = []
        self.swapping = False

        for window in self.start_positions.keys():
            self.add_window(window)

    def add_window(self, window):
        """Adds a window to the BSP tree"""
        if not self.valid_window(window):
            return False
        self.windows.append(window)
        window.tiler = self
        if window not in self.start_positions.keys():
            self.start_positions[window] = window.display_size

            rules = config.GET_RULES(window.classname)
            if rules is not None and re.search(rules["regex"], window.title) is not None:
                if "floating" in rules:
                    window.set_floating(rules["floating"])
                if "decorated" in rules:
                    if bool(rules["decorated"]):
                        window.enable_decoration()
                    else:
                        window.disable_decoration()
                if "position" in rules:
                    window.move_to(tuple(rules["position"]))
        return True

    def remove_window(self, window):
        if window in self.windows:
            self.windows.remove(window)
            window.tiler = None
            return True
        return False

    def remove_window_by_handle(self, hwnd):
        for w in self.windows:
            if w.handle == hwnd:
                return self.remove_window(w)
        return False

    def valid_window(self, window):
        return self.valid_window_by_handle(window.handle) and window.should_manage(self.monitor.display_size) and window not in self.windows

    def valid_window_by_handle(self, handle):
        # check config rules
        if win32gui.GetClassName(handle) in config.IGNORED_CLASSNAMES() or win32gui.GetWindowText(handle) in config.IGNORED_WINDOW_TITLES():
            return False
        return True

    def get_window_from_handle(self, handle):
        for w in self.windows:
            if w.handle == handle:
                return w
        return None

    def contains_window_by_handle(self, handle):
        return any([w.handle == handle for w in self.windows])

    def swap_windows(self, a, b):
        if a not in self.windows or b not in self.windows or a.is_floating() or b.is_floating() or self.swapping:
            return
        print('swapping {0} and {1}'.format(a.title[:30], b.title[:30]))
        region_a = a.region
        region_b = b.region

        # simulate a mouse release to stop dragging the window
        try:
            x, y = win32api.GetCursorPos()
            win32api.mouse_event(MOUSEEVENTF_ABSOLUTE + MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        except win32api.error:
            print('error faking drag release during window swap')

        self.swapping = True
        self.__move_window_to_region(a, region_b)
        self.__move_window_to_region(b, region_a)
        self.swapping = False

    def tile_windows(self):
        if self.swapping:
            return
        region = add_margin(self.monitor.display_size, config.DISPLAY_PADDING())
        self.__tile_area(region, [w for w in self.windows if not w.is_floating() and not w.do_not_manage])

    def __move_window_to_region(self, window, region):
        # save given region for window swapping
        window.region = region
        # apply margins and move
        region = add_margin(region, config.WINDOW_MARGIN())

        # special regions
        if window.classname in config.SPECIAL_MARGINS():
            # check the regex
            special_margin = config.SPECIAL_MARGINS()[window.classname]
            if re.search(special_margin[0], window.title) is not None:
                region = add_margin(region, special_margin[1])

        window.move_to(region)

    def __tile_area(self, area, windows):
        if len(windows) == 0:
            return
        if len(windows) == 1:
            # we've found a region for the window
            self.__move_window_to_region(windows[0], area)
            return
        
        left, top, right, bottom = area
        width = right - left
        height = bottom - top
        horizontal_split = True if width >= height else False

        width //= 2
        height //= 2
        if horizontal_split:
            regions = [
                (left, top, left + width, bottom),
                (left + width, top, right, bottom)
            ]
        else:
            regions = [
                (left, top, right, top + height),
                (left, top + height, right, bottom)
            ]
        windows_by_region = [[], []]
        sorted_windows = sorted(windows, key=lambda w: w.display_area, reverse=True)
        for w in sorted_windows:
            if len(windows_by_region[0]) == len(windows_by_region[1]):
                # tree is currently balanced, keep window in closest region
                overlap = [overlap_area(w.display_size, r) if check_overlap(w.display_size, r) else 0 for r in regions]
                if overlap[0] >= overlap[1]:
                    windows_by_region[0].append(w)
                else:
                    windows_by_region[1].append(w)
            else:
                # tree is unbalanced, add to less full region
                if len(windows_by_region[0]) < len(windows_by_region[1]):
                    windows_by_region[0].append(w)
                else:
                    windows_by_region[1].append(w)
        for i in range(2):
            self.__tile_area(regions[i], windows_by_region[i])
                

    def restore_positions(self, positions):
        """Restores all windows to the given positions"""
        for window, position in positions.items():
            # result = window.enable_decoration()
            # if not result:
            #     print('error setting window decoration')
            result = window.set_floating(False)
            if not result:
                print('error setting window to non-floating')
            if window in self.windows:
                window.move_to(position)

    def restore_window_position(self, positions, window):
        result = window.set_floating(False)
        if not result:
            print('error setting window to non-floating')
        if window in self.windows:
            window.move_to(positions[window])
   
import time
import threading
import sys
import win32gui
import win32api
import ctypes
import ctypes.wintypes

from win32con import EVENT_MIN
from win32con import EVENT_MAX
from win32con import WINEVENT_OUTOFCONTEXT
from win32con import WM_QUIT
from win32con import MONITOR_DEFAULTTONEAREST

from win32con import EVENT_OBJECT_CREATE
from win32con import EVENT_OBJECT_DESTROY
from win32con import EVENT_OBJECT_SHOW
from win32con import EVENT_OBJECT_HIDE
from win32con import EVENT_OBJECT_FOCUS
from win32con import EVENT_OBJECT_LOCATIONCHANGE
from win32con import EVENT_SYSTEM_MINIMIZEEND
from win32con import EVENT_SYSTEM_MINIMIZESTART
from win32con import EVENT_SYSTEM_DRAGDROPSTART
from win32con import EVENT_SYSTEM_DRAGDROPEND

from wmpy.monitor import Monitor
from wmpy.window import Window
from wmpy.tiler import Tiler, check_overlap, overlap_area
import wmpy.config as config

class WindowManager(object):

    def __init__(self):
        self.lastWindowSwap = 0

        monitors = Monitor.get_displays()
        self.tilers = []
        for monitor in monitors:
            self.tilers.append(Tiler(monitor))

    def get_monitor_from_window_handle(self, hwnd):
        mhwnd = win32api.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        for t in self.tilers:
            if t.monitor.handle == mhwnd:
                return t.monitor
        return None

    def get_tiler_from_window_handle(self, hwnd):
        monitorHwnd = win32api.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
        for t in self.tilers:
            if t.monitor.handle == monitorHwnd:
                return t
        return None

    def print_event(self, hwnd, dwmsEventTime):
        print(hwnd)

    def on_create_object(self, hwnd, dwmsEventTime):
        # this is so dirty, but can't get anything else to work :/
        for t in self.tilers:
            retile = False
            current = [w for w in t.windows]
            new = []
            for w in t.monitor.get_window_positions().keys():
                new.append(w)
            for w in new:
                if w not in current:
                    result = t.add_window(w)
                    if result:
                        retile = True
            for w in current:
                if w not in new:
                    result = t.remove_window(w)
                    if result:
                        retile = True
            if retile:
                t.tile_windows()

    def on_destroy_object(self, hwnd, dwmsEventTime):
        for t in self.tilers:
            if t.contains_window_by_handle(hwnd):
                if t.remove_window_by_handle(hwnd):
                    t.tile_windows()
                else:
                    print('Error removing window from tiler', win32gui.GetWindowText(hwnd), win32gui.GetClassName(hwnd))

    def on_location_change(self, hwnd, dwmsEventTime):
        for t in self.tilers:
            if t.contains_window_by_handle(hwnd):
                window = t.get_window_from_handle(hwnd)
                if check_overlap(t.monitor.display_size, window.display_size):
                    area = overlap_area(t.monitor.display_size, window.display_size)
                    if area / window.display_area < config.DISPLAY_SWAP_OVERLAP_THRESHOLD():
                        # swap displays
                        self.__swap_displays(t, hwnd)
                        return
                    elif dwmsEventTime - self.lastWindowSwap > config.WINDOW_SWAP_TIMEOUT():
                        # moved on current monitor
                        for w in t.windows:
                            if w != window and check_overlap(w.display_size, window.display_size):
                                area = overlap_area(w.display_size, window.display_size)
                                if area / window.display_area >= config.WINDOW_SWAP_OVERLAP_THRESHOLD():
                                    # swap windows
                                    self.lastWindowSwap = dwmsEventTime
                                    t.swap_windows(window, w)
                                    break
                        return
                else:
                    # no overlap, swap displays
                    self.__swap_displays(t, hwnd)
                    return

    def __swap_displays(self, tiler, window_hwnd):
        tiler.remove_window_by_handle(window_hwnd)
        time.sleep(config.DISPLAY_MOVE_TIMEOUT())
        tiler.tile_windows()
        self.on_create_object(window_hwnd)

    def start(self):
        for tiler in self.tilers:
            tiler.tile_windows()

        MESSAGE_MAP = {
            EVENT_OBJECT_CREATE: self.on_create_object,
            EVENT_OBJECT_DESTROY: self.on_destroy_object,
            EVENT_OBJECT_LOCATIONCHANGE: self.on_location_change,
            EVENT_SYSTEM_MINIMIZESTART: self.on_create_object,
            EVENT_SYSTEM_MINIMIZEEND: self.on_create_object,
            EVENT_OBJECT_HIDE: self.on_create_object,
            EVENT_SYSTEM_DRAGDROPSTART: self.print_event,
            EVENT_SYSTEM_DRAGDROPEND: self.print_event
        }

        user32 = ctypes.windll.user32
        ole32 = ctypes.windll.ole32

        ole32.CoInitialize(0)

        WinEventProcType = ctypes.WINFUNCTYPE(
            None, 
            ctypes.wintypes.HANDLE,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LONG,
            ctypes.wintypes.LONG,
            ctypes.wintypes.DWORD,
            ctypes.wintypes.DWORD
        )

        def win_error(result, func, args):
            if not result:
                raise ctypes.WinError(ctypes.get_last_error())
            return args

        def callback(hWinEventHook, event, hwnd, idObject, idChild, dwEventThread, dwmsEventTime):
            func = MESSAGE_MAP.get(event)
            if func is not None:
                func(hwnd, dwmsEventTime)

        self.WinEventProc = WinEventProcType(callback)

        user32.SetWinEventHook.restype = ctypes.wintypes.HANDLE
        user32.SetWinEventHook.errcheck = win_error

        thread = threading.Thread(target=self.msg_loop, args=(user32, ole32))
        thread.start()
        return thread.ident

    def msg_loop(self, user32, ole32):
        hook = user32.SetWinEventHook(
            EVENT_MIN,
            EVENT_MAX,
            0,
            self.WinEventProc,
            0,
            0,
            WINEVENT_OUTOFCONTEXT
        )
        if hook == 0:
            print('SetWinEventHook failed')
            sys.exit(1)

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            user32.TranslateMessageW(msg)
            user32.DispatchMessageW(msg)

        user32.UnhookWinEvent(hook)
        ole32.CoUninitialize()

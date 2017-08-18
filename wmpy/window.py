import win32api
import win32gui

from win32con import SWP_FRAMECHANGED
from win32con import SWP_NOMOVE
from win32con import SWP_NOSIZE
from win32con import SWP_NOZORDER

from win32con import WM_CLOSE

from win32con import GWL_STYLE
from win32con import GWL_EXSTYLE

from win32con import GW_OWNER

from win32con import WS_EX_TOOLWINDOW
from win32con import WS_EX_APPWINDOW
from win32con import WS_EX_WINDOWEDGE

from win32con import *

from wmpy.tiler import check_overlap, overlap_area

class Window(object):

    def __init__(self, handle):
        self.handle = handle

    def __eq__(self, other):
        return int(self.handle) == int(other.handle)

    def __hash__(self):
        return hash(self.handle)

    def __str__(self):
        try:
            left, top, right, bottom = self.display_size
            title = self.title
            classname = self.classname
            return "{title} [{classname}] ({width}x{height} @ ({left}, {top}) [{handle}]".format(
                title=title,
                classname=classname,
                left=left,
                top=top,
                width=right - left,
                height=bottom - top,
                handle=self.handle
            )
        except TypeError:
            # window may be destroyed, leading to properties returning None
            return 'Destroyed window [{0}]'.format(self.handle)

    def print_window_styles(self):
        styles = {
            GWL_STYLE: (
                ('WS_BORDER', WS_BORDER),
                ('WS_CAPTION', WS_CAPTION),
                ('WS_CHILD', WS_CHILD),
                ('WS_CHILDWINDOW', WS_CHILDWINDOW),
                ('WS_CLIPCHILDREN', WS_CLIPCHILDREN),
                ('WS_CLIPSIBLINGS', WS_CLIPSIBLINGS),
                ('WS_DISABLED', WS_DISABLED),
                ('WS_DLGFRAME', WS_DLGFRAME),
                ('WS_GROUP', WS_GROUP),
                ('WS_HSCROLL', WS_HSCROLL),
                ('WS_ICONIC', WS_ICONIC),
                ('WS_MAXIMIZE', WS_MAXIMIZE),
                ('WS_MAXIMIZEBOX', WS_MAXIMIZEBOX),
                ('WS_MINIMIZE', WS_MINIMIZE),
                ('WS_MINIMIZEBOX', WS_MINIMIZEBOX),
                ('WS_OVERLAPPED', WS_OVERLAPPED),
                ('WS_OVERLAPPEDWINDOW', WS_OVERLAPPEDWINDOW),
                ('WS_POPUP', WS_POPUP),
                ('WS_POPUPWINDOW', WS_POPUPWINDOW),
                ('WS_SIZEBOX', WS_SIZEBOX),
                ('WS_SYSMENU', WS_SYSMENU),
                ('WS_TABSTOP', WS_TABSTOP),
                ('WS_THICKFRAME', WS_THICKFRAME),
                ('WS_TILED', WS_TILED),
                ('WS_TILEDWINDOW', WS_TILEDWINDOW),
                ('WS_VISIBLE', WS_VISIBLE),
                ('WS_VSCROLL', WS_VSCROLL)
            ),
            GWL_EXSTYLE: (
                ('WS_EX_ACCEPTFILES', WS_EX_ACCEPTFILES),
                ('WS_EX_APPWINDOW', WS_EX_APPWINDOW),
                ('WS_EX_CLIENTEDGE', WS_EX_CLIENTEDGE),
                ('WS_EX_COMPOSITED', WS_EX_COMPOSITED),
                ('WS_EX_CONTEXTHELP', WS_EX_CONTEXTHELP),
                ('WS_EX_CONTROLPARENT', WS_EX_CONTROLPARENT),
                ('WS_EX_DLGMODALFRAME', WS_EX_DLGMODALFRAME),
                ('WS_EX_LAYERED', WS_EX_LAYERED),
                ('WS_EX_LAYOUTRTL', WS_EX_LAYOUTRTL),
                ('WS_EX_LEFT', WS_EX_LEFT),
                ('WS_EX_LEFTSCROLLBAR', WS_EX_LEFTSCROLLBAR),
                ('WS_EX_LTRREADING', WS_EX_LTRREADING),
                ('WS_EX_MDICHILD', WS_EX_MDICHILD),
                ('WS_EX_NOACTIVATE', WS_EX_NOACTIVATE),
                ('WS_EX_NOINHERITLAYOUT', WS_EX_NOINHERITLAYOUT),
                ('WS_EX_NOPARENTNOTIFY', WS_EX_NOPARENTNOTIFY),
                ('WS_EX_OVERLAPPEDWINDOW', WS_EX_OVERLAPPEDWINDOW),
                ('WS_EX_PALETTEWINDOW', WS_EX_PALETTEWINDOW),
                ('WS_EX_RIGHT', WS_EX_RIGHT),
                ('WS_EX_RIGHTSCROLLBAR', WS_EX_RIGHTSCROLLBAR),
                ('WS_EX_RTLREADING', WS_EX_RTLREADING),
                ('WS_EX_STATICEDGE', WS_EX_STATICEDGE),
                ('WS_EX_TOOLWINDOW', WS_EX_TOOLWINDOW),
                ('WS_EX_TOPMOST', WS_EX_TOPMOST),
                ('WS_EX_TRANSPARENT', WS_EX_TRANSPARENT),
                ('WS_EX_WINDOWEDGE', WS_EX_WINDOWEDGE)
            )
        }
        for style in styles.items():
            value = win32gui.GetWindowLong(self.handle, style[0])
            for i in range(0, len(style[1]), 2):
                if i + 1 == len(style[1]):
                    print('{0:32} : {1:d}'.format(style[1][i][0], bool(value & style[1][i][1])))
                    continue
                s1 = style[1][i]
                s2 = style[1][i + 1]
                print('{0:32} : {1:d}    {2:32} : {3:d}'.format(s1[0], bool(value & s1[1]), s2[0], bool(value & s2[1])))

    def should_manage(self, monitor_display_size):
        if win32gui.IsWindowVisible(self.handle) and not win32gui.IsIconic(self.handle):
            style_value = win32gui.GetWindowLong(self.handle, GWL_STYLE)
            if style_value & WS_MAXIMIZEBOX:
                return True
            ex_style_value = win32gui.GetWindowLong(self.handle, GWL_EXSTYLE)
        return False

    def move_to(self, position):
        try:
            win32gui.MoveWindow(
                self.handle,
                position[0],
                position[1],
                position[2] - position[0],
                position[3] - position[1],
                True
            )
            win32gui.UpdateWindow(self.handle)
            return True
        except win32gui.error:
            return False

    def update(self):
        try:
            win32gui.SetWindowPos(
                self.handle,
                0,
                0,
                0,
                0,
                0,
                SWP_FRAMECHANGED + SWP_NOMOVE + SWP_NOSIZE + SWP_NOZORDER
            )
            return True
        except win32gui.error:
            return False

    @property
    def display_area(self):
        left, top, right, bottom = self.display_size
        return (right - left) * (bottom - top)

    @property
    def display_size(self):
        try:
            return win32gui.GetWindowRect(self.handle)
        except win32gui.error:
            return None

    @property
    def title(self):
        try:
            return win32gui.GetWindowText(self.handle)
            try:
                title = title.encode('utf-8')
                title = title.decode('utf-8')
            except UnicodeEncodeError:
                title = "Couldn't encode title!"
            finally:
                return title
        except win32gui.error:
            return None

    @property
    def classname(self):
        try:
            return win32gui.GetClassName(self.handle) 
        except win32gui.error:
            return None

    @staticmethod
    def get_windows_from_monitor(monitor):
        def callback(wHandle, results):
            window = Window(wHandle)
            if window.should_manage(monitor.display_size) and monitor.contains_window(window):
                results.append(window)
                return True

        windows = []
        win32gui.EnumWindows(callback, windows)

        return windows

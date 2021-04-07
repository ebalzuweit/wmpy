"""Entry point for wmpy"""
import ctypes
import os
import win32con
import wx
import wx.adv

from wmpy.manager import WindowManager
from wmpy.window import Window
import wmpy.config as config

TRAY_TOOLTIP = 'wmpy'
TRAY_ICON_PATH = os.path.join(os.getcwd(), 'icon', 'icon.ico')


def get_monitor_descriptor(monitor):
    left, top, right, bottom = monitor.display_resolution
    return "{width}x{height} Display{primary}".format(
        width=right - left,
        height=bottom - top,
        primary=" [PRIMARY]" if monitor.is_main() else ""
    )


def get_window_descriptor(window):
    TITLE_LIMIT = 42
    label = window.title
    if len(label) > TITLE_LIMIT:
        label = label[:TITLE_LIMIT] + '...'
    return label


class wmpyTaskBar(wx.adv.TaskBarIcon):
    def __init__(self):
        super(wx.adv.TaskBarIcon, self).__init__()
        self.set_icon(TRAY_ICON_PATH)
        self.start()
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_clicked)

    def start(self):
        self.wm = WindowManager()
        self.thread_id = self.wm.start()

    def CreatePopupMenu(self):
        menu = wx.Menu()

        # refresh
        refresh_item = menu.Append(wx.NewIdRef(), 'Refresh')
        self.Bind(wx.EVT_MENU, self.on_refresh, id=refresh_item.GetId())
        menu.AppendSeparator()

        # tilers
        self.windowMap = {}
        for tiler in self.wm.tilers:
            # submenu for each display tiler
            tiler_submenu = wx.Menu()
            label = get_monitor_descriptor(tiler.monitor)
            menu.AppendSubMenu(tiler_submenu, label)

            # show windows under submenu, with check for floating
            for window in tiler.windows:
                label = get_window_descriptor(window)
                window_item = tiler_submenu.AppendCheckItem(
                    wx.NewIdRef(), label)
                window_item.Check(window.is_floating())
                self.Bind(wx.EVT_MENU, self.float_clicked,
                          id=window_item.GetId())
                self.windowMap[window_item.GetId()] = window

        # exit
        menu.AppendSeparator()
        exitItem = menu.Append(wx.ID_EXIT, 'Exit')
        self.Bind(wx.EVT_MENU, self.on_exit, exitItem)

        return menu

    def set_icon(self, path):
        icon = wx.Icon()
        icon.LoadFile(path)
        self.SetIcon(icon, TRAY_TOOLTIP)

    def float_clicked(self, event):
        window = self.windowMap[event.GetId()]
        result = window.set_floating(not window.is_floating())
        if result:
            window.tiler.tile_windows()

    def on_clicked(self, event):
        # when taskbar icon is clicked
        self.on_refresh(event)

    def on_refresh(self, event):
        config.load_config()
        for tiler in self.wm.tilers:
            tiler.tile_windows()
        self.ShowBalloon('wmpy', 'Refreshed and Retiled!')

    def on_exit(self, event):
        ctypes.windll.user32.PostThreadMessageW(
            self.thread_id, win32con.WM_QUIT, 0, 0)

        for tiler in self.wm.tilers:
            tiler.restore_positions(tiler.start_positions)

        wx.CallAfter(self.Destroy)


def main():
    app = wx.App()
    taskbar = wmpyTaskBar()
    app.MainLoop()


if __name__ == '__main__':
    main()

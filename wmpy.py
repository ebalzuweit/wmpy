"""Entry point for wmpy"""
import ctypes
import os

from win32con import WM_QUIT
from wx.adv import TaskBarIcon

from wx import NewId
from wx import MenuItem
from wx import EVT_MENU
from wx.adv import EVT_TASKBAR_LEFT_DOWN
from wx import Menu
from wx import BITMAP_TYPE_PNG
from wx import Icon
from wx import CallAfter
from wx import App

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

def get_monitor_info(monitor):
    return str(int(monitor.handle))

def get_window_descriptor(window):
    return window.title

def get_window_info(window):
    print(window)
    window.print_window_styles()
    return "{0} [{1}]".format(window.classname, window.handle)

class wmpyTaskBar(TaskBarIcon):
    def __init__(self):
        super(TaskBarIcon, self).__init__()
        self.set_icon(TRAY_ICON_PATH)
        self.start()
        self.Bind(EVT_TASKBAR_LEFT_DOWN, self.on_clicked)

    def start(self):
        self.wm = WindowManager()
        self.thread_id = self.wm.start()
    
    def CreatePopupMenu(self):
        if not hasattr(self, 'exitID'):
            self.refreshID = NewId()
            self.exitID = NewId()

            self.Bind(EVT_MENU, self.on_refresh, id=self.refreshID)
            self.Bind(EVT_MENU, self.on_exit, id=self.exitID)

        menu = Menu()

        # Refresh
        refresh_item = MenuItem(menu, self.refreshID, 'Refresh')
        menu.Append(refresh_item)
        # Separator
        menu.AppendSeparator()
        # Displays
        self.displayMap = {}
        self.windowMap = {}
        for tiler in self.wm.tilers:
            display_submenu = Menu()

            # display info
            displayInfoID = NewId()
            self.Bind(EVT_MENU, self.display_clicked, id=displayInfoID)
            self.displayMap[displayInfoID] = tiler.monitor

            display_submenu.Append(displayInfoID, 'Get Info')

            # Windows submenus
            for window in tiler.windows:
                window_submenu = Menu()

                windowInfoID = NewId()
                self.Bind(EVT_MENU, self.window_clicked, id=windowInfoID)
                self.windowMap[windowInfoID] = window

                window_submenu.Append(windowInfoID, 'Get Info')

                floatID = NewId()
                self.Bind(EVT_MENU, self.float_clicked, id=floatID)
                self.windowMap[floatID] = window

                window_submenu.Append(
                    floatID,
                    '{0} Floating'.format('Disable' if window.is_floating() else 'Enable')
                )

                toggleDecorationID = NewId()
                self.Bind(EVT_MENU, self.toggle_decoration, id=toggleDecorationID)
                self.windowMap[toggleDecorationID] = window

                window_submenu.Append(
                    toggleDecorationID,
                    '{0} Decoration'.format('Disable' if window.is_decorated else 'Enable')
                )

                windowID = NewId()
                self.Bind(EVT_MENU, self.window_clicked, id=windowID)
                self.windowMap[windowID] = window

                display_submenu.Append(windowID, get_window_descriptor(window), window_submenu)

            # display submenu
            displayID = NewId()
            self.Bind(EVT_MENU, self.display_clicked, id=displayID)
            self.displayMap[displayID] = tiler.monitor

            menu.Append(displayID, get_monitor_descriptor(tiler.monitor), display_submenu)
        # Separator
        menu.AppendSeparator()
        # Exit
        menu.Append(self.exitID, 'Exit')

        return menu

    def set_icon(self, path):
        icon = Icon()
        icon.LoadFile(path)
        self.SetIcon(icon, TRAY_TOOLTIP)

    def float_clicked(self, event):
        window = self.windowMap[event.GetId()]
        result = window.set_floating(not window.is_floating())
        if result:
            window.tiler.tile_windows()

    def toggle_decoration(self, event):
        window = self.windowMap[event.GetId()]
        if window.is_decorated:
            if not window.disable_decoration():
                print('failed to disable decoration')
        else:
            if not window.enable_decoration():
                print('failed to enable decoration')

    def display_clicked(self, event):
        # when they click on a display
        monitor = self.displayMap[event.GetId()]
        self.ShowBalloon(get_monitor_descriptor(monitor), get_monitor_info(monitor))

    def window_clicked(self, event):
        # when they click on a window
        window = self.windowMap[event.GetId()]
        self.ShowBalloon(get_window_descriptor(window), get_window_info(window))

    def on_clicked(self, event):
        # when taskbar icon is clicked
        pass

    def on_refresh(self, event):
        config.load_config()
        for tiler in self.wm.tilers:
            tiler.tile_windows()
        self.ShowBalloon('wmpy', 'Refreshed and Retiled!')

    def on_exit(self, event):
        ctypes.windll.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)

        for tiler in self.wm.tilers:
            tiler.restore_positions(tiler.start_positions)

        CallAfter(self.Destroy)


def main():
    app = App()
    wmpyTaskBar()
    app.MainLoop()

if __name__ == '__main__':
    main()

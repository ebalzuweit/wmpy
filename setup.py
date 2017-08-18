import os
from cx_Freeze import setup, Executable

base = "Win32GUI"

executables = [Executable(
    script="wmpy.py",
    base=base,
    icon=os.path.join('icon', 'icon.ico')
)]
packages = []
options = {
    "build_exe": {
        "packages": packages,
        "include_files": ['icon', 'config.json']
    },
}

setup(
    name="wmpy",
    options=options,
    version="0.8.0",
    description="window manager in python",
    executables=executables
)
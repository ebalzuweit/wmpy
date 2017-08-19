"""Configuration file"""
import json
import os
import re

CONFIG_FILE = 'config.json'

data = None
def load_config():
    global data
    path = os.path.join(os.getcwd(), CONFIG_FILE)
    with open(path, 'r') as f:
        data = json.loads(f.read())
load_config()

def DISPLAY_PADDING():
    return data["DisplayPadding"]

def WINDOW_MARGIN():
    return data["WindowMargin"]

def WINDOW_SWAP_OVERLAP_THRESHOLD():
    return data["WindowSwapOverlapThreshold"]

def WINDOW_SWAP_TIMEOUT():
    return data["WindowSwapTimeout"]

def DISPLAY_SWAP_OVERLAP_THRESHOLD():
    return data["DisplaySwapOverlapThreshold"]

def DISPLAY_MOVE_TIMEOUT():
    return data["DisplayMoveTimeout"]

def IGNORED_CLASSNAMES():
    return data["IgnoredClassNames"]

def IGNORED_WINDOW_TITLES():
    return data["IgnoredWindowTitles"]

def SPECIAL_MARGINS():
    return data["SpecialMargins"]

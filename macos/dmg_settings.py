# dmg_settings.py — dmgbuild 設定檔
import os

APP_PATH = "dist/IP Service Checker.app"
APP_NAME = os.path.basename(APP_PATH)

application    = APP_PATH
appname        = APP_NAME
format         = "UDZO"           # 壓縮格式
size           = None
files          = [APP_PATH]
symlinks       = {"Applications": "/Applications"}
icon_locations = {
    APP_NAME:       (150, 180),
    "Applications": (450, 180),
}
background     = "builtin-arrow"
window_rect    = ((200, 200), (620, 400))
icon_size      = 120
text_size      = 14

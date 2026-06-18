from setuptools import setup

APP      = ["ip-service_check_app.py"]
APP_NAME = "IP Service Checker"

OPTIONS = {
    "argv_emulation": False,
    "iconfile": "icon.icns",
    "plist": {
        "CFBundleName":               APP_NAME,
        "CFBundleDisplayName":        APP_NAME,
        "CFBundleIdentifier":         "com.leifeng.ipchecker",
        "CFBundleVersion":            "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleIconFile":           "icon",
        "NSHighResolutionCapable":    True,
        "NSRequiresAquaSystemAppearance": False,
    },
    "packages": [
        "webview",
        "requests",
        "urllib3",
        "certifi",
        "charset_normalizer",
        "chardet",
        "idna",
        "email",
        "html",
        "http",
    ],
    "excludes": [
        "tkinter", "unittest",
        "xmlrpc", "pydoc", "doctest", "argparse",
    ],
}

setup(
    app=APP,
    name=APP_NAME,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

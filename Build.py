# This command is used to build the executable file
# pyinstaller main.py --name 'DJIM3TThermalConverter' --noconsole --onefile

import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--noconsole'
])

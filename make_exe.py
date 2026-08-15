import os
import sys

# Script helper per la compilazione in file .exe tramite PyInstaller
BUILD_SCRIPT = """
import PyInstaller.__main__
import sys

PyInstaller.__main__.run([
    'main.py',
    '--onefile',
    '--name=AmazonPriceTrackerBot',
    '--clean',
    '--hidden-import=telegram',
    '--hidden-import=telegram.ext',
    '--hidden-import=apscheduler',
    '--hidden-import=bs4',
    '--hidden-import=lxml',
    '--hidden-import=requests',
    '--hidden-import=dotenv',
    '--hidden-import=amazon_super_deals',
    '--hidden-import=amazon_deals_scraper',
    '--hidden-import=deduplicator',
])
"""

if __name__ == "__main__":
    with open("build_exe.py", "w", encoding="utf-8") as f:
        f.write(BUILD_SCRIPT)
    print("Script build_exe.py creato con successo.")

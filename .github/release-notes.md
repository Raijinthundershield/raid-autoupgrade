## Raid Autoupgrade — Windows download

Download `RaidAutoupgrade-v<version>-win64.exe` below and double-click it. No
Python, Node, or command line required. The app asks for administrator rights
once at launch (it needs them to switch your network adapter on and off for the
airplane-mode trick).

### Before you run it

**Microsoft Edge WebView2 runtime** — the app renders its window through this
runtime. It ships preinstalled on current Windows 10 and 11, so you almost
certainly already have it. If it is missing, the app opens the download page for
you; you can also get it ahead of time from <https://aka.ms/webview2>.

### "Windows protected your PC" (SmartScreen)

This exe is **unsigned**, so the first time you run it Windows SmartScreen shows
a blue *"Windows protected your PC"* dialog. This is expected for any new app
without a paid code-signing certificate — it is not a sign the app is malware.
To proceed:

1. Click **More info**.
2. Click **Run anyway**.

Your antivirus may also flag a brand-new unsigned exe; allow it if so.

### Notes

- **First launch is slow.** The exe is a single self-contained file (~150 MB of
  OpenCV/NumPy/WebView). It unpacks to a temp folder each time it starts, so the
  very first launch takes a while. Subsequent launches are quicker.
- **Something went wrong?** If the app fails to start, it writes a log to
  `%PROGRAMDATA%\RaidAutoupgrade\logs\app.log`. Include that file when reporting
  an issue.

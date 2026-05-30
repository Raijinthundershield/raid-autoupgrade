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

### Antivirus / Windows Defender ("Threat blocked")

Windows Defender (or another antivirus) may flag this exe — typically as
something like `Trojan:Win32/Sabsik.*!ml` or `Wacatac.*!ml` — and quarantine or
delete it. **This is a false positive.** The `!ml` suffix means it was guessed
by a machine-learning heuristic, not matched against known malware. It happens
to almost every unsigned, single-file PyInstaller app: the exe unpacks itself to
a temp folder and runs from there, which the heuristic scores as suspicious even
though it is exactly how this packaging format works.

If Defender removed the file:

1. Open **Windows Security → Virus & threat protection → Protection history**.
2. Find the blocked item, expand **Actions**, and choose **Restore** (or
   **Allow on device**).
3. If it was deleted, re-download it from the Releases page after allowing it.

To avoid re-quarantine you can add the exe (or its folder) as an exclusion under
**Virus & threat protection → Manage settings → Exclusions**. Only do this for a
file you downloaded from this project's official Releases page — verify the
SHA-256 shown on the asset if you want to be certain it was not tampered with.

### Notes

- **First launch is slow.** The exe is a single self-contained file (~150 MB of
  OpenCV/NumPy/WebView). It unpacks to a temp folder each time it starts, so the
  very first launch takes a while. Subsequent launches are quicker.
- **Something went wrong?** If the app fails to start, it writes a log to
  `%PROGRAMDATA%\RaidAutoupgrade\logs\app.log`. Include that file when reporting
  an issue.

## Download

Grab **`RaidAutoupgrade-v<version>-win64.exe`** below — Windows 64-bit, no Python,
Node, or command line required. The app asks for administrator rights once at
launch (it needs them to switch your network adapter on and off for the
airplane-mode trick).

**Your browser may block the download.** Because the exe is unsigned, your
browser can flag it as unsafe and refuse to save it — click **Keep** /
**Keep anyway** in the download bar to get the file.

**First launch is slow.** The single ~150 MB file (OpenCV/NumPy/WebView) unpacks
to a temp folder each time it starts, so give the very first launch 10–20
seconds. Later launches are quicker.

### "Windows protected your PC" (SmartScreen)

This exe is **unsigned**, so the first time you run it Windows SmartScreen shows
a blue *"Windows protected your PC"* dialog. This is expected for any new app
without a paid code-signing certificate — it is not a sign the app is malware.
To proceed:

1. Click **More info**.
2. Click **Run anyway**.

### Antivirus / Windows Defender ("Threat blocked")

Windows Defender (or another antivirus) may flag this exe — typically as
something like `Trojan:Win32/Sabsik.*!ml` or `Wacatac.*!ml` — and quarantine it.
**This is a false positive**, common to unsigned single-file PyInstaller apps. If
Defender removed the file:

1. Open **Windows Security → Virus & threat protection → Protection history**.
2. Find the blocked item, expand **Actions**, and choose **Restore** (or
   **Allow on device**).
3. If it was deleted, re-download it from the Releases page after allowing it.

To avoid re-quarantine you can add the exe (or its folder) as an exclusion under
**Virus & threat protection → Manage settings → Exclusions**. Only do this for a
file you downloaded from this project's official Releases page — verify the
SHA-256 shown on the asset if you want to be certain it was not tampered with.

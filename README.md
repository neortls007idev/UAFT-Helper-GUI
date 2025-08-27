# UAFT Helper GUI
A tiny cross-platform Python UI to drive **UnrealAndroidFileTool** (UAFT). It helps you discover Android devices, select your game package that exposes **Android File Server (AFS)**, push a `UECommandLine.txt` with your preferred Unreal Insights trace arguments, list/pull generated `.trace/.utrace` files from `^saved/Traces`, and—optionally—launch **UnrealInsights** on a selected capture.

> Copyright (c) 2025 **Rahul Gupta**
> Licensed under the **Apache License, Version 2.0**. You **must** retain the `LICENSE` and `NOTICE` files in redistributions and derivative works (see [License](#license)).

---
## Official Unreal Documentation for profling Android games
 
- How to use Unreal Insights to profile Android games (Unreal Engine) official Documentation: 
https://dev.epicgames.com/documentation/en-us/unreal-engine/how-to-use-unreal-insights-to-profile-android-games-for-unreal-engine

----------
## Why this exists
Working with UAFT on Android is powerful but fiddly. This GUI wraps common flows:
 -   Enumerate Android devices UAFT can see.
 -   List packages that expose the AFS receiver on a chosen device.
 -   Generate & push `UECommandLine.txt` with trace args (e.g., CPU/GPU/Frame/File).
 -   List and pull `.trace` / `.utrace` captures from `^saved/Traces` to your machine.
 
----------
## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Running](#running)
- [Quick Start](#quick-start)
- [Fields & Controls](#fields--controls)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)
- [Roadmap Ideas](#roadmap-ideas)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---
## Features
 -   **Device discovery** with make/model decoration via `adb` for readability.
 -   **Package listing (AFS)** scoped to the selected device.
 -   **Command-line injection**: creates a temp `UECommandLine.txt` and pushes it to `^commandfile`.
 -   **Trace management**: list on-device traces; pull to a local folder.
 -   **Open in Unreal Insights** after pull (optional).
 -  **Friendly errors** for common misconfigurations (wrong UAFT path, missing PySide6, etc.).

> This repository **does not** ship UAFT or Unreal Insights. You point the tool to binaries from your Unreal Engine installation.

----------
## Requirements
 - Python 3.9+
 - PySide6 (`pip install PySide6`)

  
- A working Unreal Engine installation (for UAFT and UnrealInsights)
- Your packaged Android build includes **Android File Server (AFS)** and is installed on the device.

----------
## Running

```bash
python UE_UAFT_Tool.py
```
-   The window title will read **“UAFT Helper GUI”**.

----------
## Quick Start

1.  **Point to UAFT**  
    Click **Tool Paths → Browse UAFT…** and select `UnrealAndroidFileTool.exe` (on Windows) or the platform-appropriate UAFT binary in your Engine install. If you pick a folder or a non-executable, you’ll get a clear error directing you to the proper path (usually `Engine/Binaries/DotNET/Android/<platform>/UnrealAndroidFileTool.exe`).
    
2.  **(Optional) Point to UnrealInsights**  
    Click **Browse UnrealInsights…** if you want the app to launch Insights automatically after pulling a trace. If the path is wrong, you’ll see “UnrealInsights.exe not found.”
    
3.  **Detect devices**  
    Click **List Devices** to enumerate UAFT-visible devices; the table shows Make/Model/Serial pulled via `adb`. Selecting a row fills the **Device Serial** box.
    
4.  **List packages (AFS)**  
    Click **List Packages (AFS)** and select your app’s package (e.g., `com.company.game`). The tool filters sensible package strings and sets the **Package** field when you pick one.
    
5.  **Set trace arguments**  
    The default bundle covers Bookmarks/Frame/CPU/GPU/LoadTime/File plus CPU profiler & named events. Add `-trace=default,memory` and ensure a **Development** build for Memory Insights.
    
    You can edit these before pushing.
    ```
    -tracehost=127.0.0.1 -trace=Bookmark,Frame,CPU,GPU,LoadTime,File -cpuprofilertrace -statnamedevents -filetrace -loadtimetrace
    For Memory Insights: include -trace=default,memory (and ensure Dev build)
    ```
    
6.  **Generate & Push `UECommandLine.txt`**  
    Click **Generate and Push UECommandLine.txt**. The tool writes your args to a temporary file and pushes it to `^commandfile` via UAFT.
    
7.  **Capture, then pull traces**  
    After running your game and producing traces, click **Refresh Traces** to list files under `^saved/Traces`; select one and click **Pull Selected Trace** to copy it locally. Optionally check **Open in Unreal Insights after pull**.
    
----------
## Fields & Controls

-   **Security Token / Port / Serial or IP / Package**  
    These map directly to UAFT arguments (`-k`, `-t`, `-s` or `-ip`, `-p`). When a serial is provided, IP is ignored to avoid confusing UAFT.
    
-   **Pull to**  
    Destination directory for traces; defaults to `~/UnrealTraces`. 
    
----------
## Troubleshooting

-   **“PySide6 is not installed or failed to load.”**  
    Install it with: `python -m pip install PySide6`.
  
-   **Picked a folder instead of UAFT executable**  
    You’ll see a friendly error asking you to select the actual UAFT binary (usually under `Engine/Binaries/DotNET/Android/...`).
    
-   **Permission error launching an external tool**  
    Windows SmartScreen/AV or selecting a non-executable can cause this; the error suggests unblocking or picking a proper `.exe`.
    
-   **“UnrealInsights.exe not found”**  
    Verify the Insights path in **Tool Paths**.
    
-   **No traces found**  
    If `^saved/Traces` doesn’t exist yet, UAFT may return non-zero; the tool treats that as “no traces.”

----------
## FAQ

- Does this include UAFT or Unreal Insights?
> No. It discovers and calls the copies from your Unreal Engine installation.

- Will this auto-enable AFS in my game?
> No. Your packaged build must already include the Android File Server receiver.

- Can I use IP instead of serial?
> Yes, but when a serial is set, the UI ignores IP intentionally to avoid confusing UAFT argument resolution.
    
----------
## Roadmap Ideas

-   Caching last used UAFT/Insights paths and target package (per-platform configs).
-   Multi-device multi-pull with progress UI.
-   Built-in trace arg presets (CPU-only, GPU-only, Memory Insights, Network/File, etc.).
-   One-click `adb tcpip`/port-forward setup helpers.

----------
## Contributing

Pull requests are welcome. Please ensure code is formatted and tested locally. If you add features, update this README and include brief UI notes or screenshots where helpful.

----------
## License

SPDX-License-Identifier: Apache-2.0
Copyright (c) 2025 Rahul Gupta

**You can find the complete License Agreement in the License file in the repository**.

----------
## Acknowledgements

- **Author**: [Rahul Gupta](https://www.rahulguptagamedev.com/)
-   Built around Epic’s **UnrealAndroidFileTool** and **Unreal Insights**.
-   UI: **PySide6 / Qt**.
----------

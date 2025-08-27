# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2025 Rahul Gupta

"""
UAFT Helper GUI – A tiny cross‑platform Python UI to drive UnrealAndroidFileTool

What it does
- Lists Android devices UAFT can see
- Lists packages with AndroidFileServer (AFS) receiver
- Generates and pushes UECommandLine.txt with your chosen trace args
- Pulls .trace/.utrace files from ^saved/Traces to your PC
- Opens UnrealInsights.exe on a selected trace (optional)

Requirements
- Python 3.9+
- PySide6 (pip install PySide6)
- A working Unreal Engine install (for UAFT and UnrealInsights)
- Your packaged Android build includes Android File Server (AFS) and is installed on the device

Tested on Windows; should also work on macOS/Linux with paths adjusted.
"""

import os
import sys
import subprocess
import threading
from pathlib import Path
from datetime import datetime

# Try importing PySide6 with a friendly error if missing
try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (
        QApplication, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QLineEdit, QTextEdit, QListWidget, QListWidgetItem, QGroupBox,
        QMessageBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QAbstractItemView
    )
except Exception as _e:  # ImportError/ModuleNotFoundError
    print("*** PySide6 is not installed or failed to load. ***")
    print("Fix: run 'python -m pip install PySide6' in the same environment.")
    print(f"Original import error: {_e}")
    raise

# ---- defaults / presets ----
DEFAULT_TRACE_ARGS = (
    "-tracehost=127.0.0.1 -trace=Bookmark,Frame,CPU,GPU,LoadTime,File "
    "-cpuprofilertrace -statnamedevents -filetrace -loadtimetrace\n"
    "For Memory Insights: include -trace=default,memory (and ensure Dev build)\n"
)

# ------------------------- helpers -------------------------

def run(cmd:list[str], cwd:Path|None=None) -> tuple[int,str,str]:
    try:
        proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, shell=False)
    except PermissionError as e:
        # Common on Windows when selecting a folder instead of the .exe,
        # or when the file is blocked by SmartScreen/AV.
        raise RuntimeError(f"Permission error launching: {cmd[0]} — check that it's an executable (.exe on Windows) and not blocked (Right‑click > Properties > Unblock). Original: {e}")
    out, err = proc.communicate()
    return proc.returncode, out, err


def path_exists(p:str) -> bool:
    return Path(p).expanduser().exists()


# ------------------------- core UAFT driver -------------------------
class UAFT:
    def __init__(self, uaft_path:Path):
        self.uaft_path = uaft_path

    def _base_args(self, serial:str|None, ip:str|None, port:str|None, package:str|None, token:str|None):
        args = [str(self.uaft_path)]
        # Prefer serial over IP; if serial is provided, ignore IP to avoid confusing UAFT
        if serial:
            args += ["-s", serial]
        elif ip:
            args += ["-ip", ip]
        if port:
            args += ["-t", port]
        if package:
            args += ["-p", package]
        if token:
            args += ["-k", token]
        return args

    def devices(self) -> list[str]:
        code, out, err = run([str(self.uaft_path), "devices"])   # UAFT prints list
        if code != 0:
            raise RuntimeError(err or out)
        # filter lines that look like device serials
        lines = [ln.strip().lstrip("@") for ln in out.splitlines() if ln.strip()]
        # Heuristic: serial lines have no spaces
        return [ln for ln in lines if " " not in ln and ln.lower() != "devices"]

    def packages(self, serial:str|None=None) -> list[str]:
        args = [str(self.uaft_path)]
        if serial:
            args += ["-s", serial]
        args += ["packages"]
        code, out, err = run(args)
        if code != 0:
            raise RuntimeError(err or out)
        return [ln.strip() for ln in out.splitlines() if ln.strip() and "." in ln]

    def push_commandfile(self, serial:str|None, ip:str|None, port:str|None, package:str, token:str|None, local_cmd:str):
        # UAFT: push <local> ^commandfile
        args = self._base_args(serial, ip, port, package, token) + ["push", local_cmd, "^commandfile"]
        code, out, err = run(args)
        if code != 0:
            raise RuntimeError(err or out)
        return out

    def list_traces(self, serial:str|None, ip:str|None, port:str|None, package:str, token:str|None) -> list[str]:
        # UAFT: ls -R ^saved/Traces
        args = self._base_args(serial, ip, port, package, token) + ["ls", "-R", "^saved/Traces"]
        code, out, err = run(args)
        if code != 0:
            # If folder missing, UAFT returns non-zero; treat as no traces
            return []
        files = []
        for ln in out.splitlines():
            ln = ln.strip()
            if ln.endswith(".trace") or ln.endswith(".utrace"):
                files.append(ln)
        return files

    def pull_trace(self, serial:str|None, ip:str|None, port:str|None, package:str, token:str|None, remote_file:str, local_dir:Path) -> Path:
        local_dir.mkdir(parents=True, exist_ok=True)
        args = self._base_args(serial, ip, port, package, token) + ["pull", remote_file, str(local_dir)]
        code, out, err = run(args)
        if code != 0:
            raise RuntimeError(err or out)
        return local_dir/Path(remote_file).name

# ------------------------- UI -------------------------
class App(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UAFT Helper GUI")
        self.resize(900, 680)

        self.uaft_path = QLineEdit()
        self.btn_browse_uaft = QPushButton("Browse UAFT…")
        self.insights_path = QLineEdit()
        self.btn_browse_insights = QPushButton("Browse UnrealInsights…")

        self.security_token = QLineEdit()
        self.port = QLineEdit()
        self.port.setPlaceholderText("57099")

        self.serial = QLineEdit(); self.serial.setPlaceholderText("auto-filled from device list")
        self.ip = QLineEdit("127.0.0.1")
        self.package = QLineEdit(); self.package.setPlaceholderText("e.g., com.company.game (no spaces/colons)")

        self.trace_args = QTextEdit()
        self.trace_args.setPlainText(DEFAULT_TRACE_ARGS)

        self.btn_detect_devices = QPushButton("List Devices")
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

        self.device_table = QTableWidget(0, 3)
        self.device_table.setHorizontalHeaderLabels(["Make", "Model", "Serial"])
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.device_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.device_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.device_table.setMinimumHeight(160)
        self.btn_list_packages = QPushButton("List Packages (AFS)")
        self.btn_list_packages.setToolTip("AFS = Android File Server. Shows packages on the device that expose the AFS receiver for UAFT operations.")
        self.pkg_list = QListWidget()
        self.pkg_list.setSelectionMode(QListWidget.SingleSelection)
        self.pkg_list.setMinimumHeight(120)
        self.pkg_list.setToolTip("Select your game/app package (e.g., com.Company.Game)")
        self.btn_write_cmd = QPushButton("Generate and Push UECommandLine.txt")

        self.btn_refresh_traces = QPushButton("Refresh Traces")
        self.trace_list = QListWidget(); self.trace_list.setSelectionMode(QListWidget.SingleSelection); self.trace_list.setMinimumHeight(160)
        self.pull_dir = QLineEdit(str(Path.home()/"UnrealTraces"))
        self.btn_choose_dir = QPushButton("Choose Folder…")
        self.btn_pull = QPushButton("Pull Selected Trace")
        self.chk_open_insights = QCheckBox("Open in Unreal Insights after pull")
        self.log = QTextEdit(); self.log.setReadOnly(True)

        self._build_layout()
        self._connect_signals()

    def _build_layout(self):
        root = QVBoxLayout(self)

        # paths
        box_paths = QGroupBox("Tool Paths")
        lp = QVBoxLayout()
        lp.addLayout(self._row([QLabel("UAFT executable:"), self.uaft_path, self.btn_browse_uaft]))
        lp.addLayout(self._row([QLabel("UnrealInsights executable (optional):"), self.insights_path, self.btn_browse_insights]))
        box_paths.setLayout(lp)

        # conn
        box_conn = QGroupBox("Connection")
        lc = QVBoxLayout()
        lc.addLayout(self._row([QLabel("Security Token:"), self.security_token, QLabel("Port:"), self.port]))
        lc.addLayout(self._row([QLabel("Device Serial:"), self.serial, QLabel("or IP:"), self.ip, QLabel("Package:"), self.package]))
        lc.addLayout(self._row([self.btn_detect_devices, self.btn_list_packages]))
        lc.addWidget(self.device_table)
        lc.addWidget(self.pkg_list)
        box_conn.setLayout(lc)

        # trace args
        box_args = QGroupBox("Trace Arguments / Command Line Arguments (UECommandLine.txt)")
        la = QVBoxLayout(); la.addWidget(self.trace_args); la.addWidget(self.btn_write_cmd)
        box_args.setLayout(la)

        # traces
        box_traces = QGroupBox("Traces on Device")
        lt = QVBoxLayout()
        lt.addLayout(self._row([self.btn_refresh_traces]))
        lt.addWidget(self.trace_list)
        lt.addLayout(self._row([QLabel("Pull to:"), self.pull_dir, self.btn_choose_dir, self.btn_pull, self.chk_open_insights]))
        box_traces.setLayout(lt)

        root.addWidget(box_paths)
        root.addWidget(box_conn)
        root.addWidget(box_args)
        root.addWidget(box_traces)
        root.addWidget(QLabel("Log"))
        root.addWidget(self.log)

    def _row(self, widgets:list):
        h = QHBoxLayout()
        for w in widgets:
            h.addWidget(w)
        h.addStretch(1)
        return h

    def _connect_signals(self):
        self.btn_browse_uaft.clicked.connect(self.pick_uaft)
        self.btn_browse_insights.clicked.connect(self.pick_insights)
        self.btn_detect_devices.clicked.connect(self.on_list_devices)
        self.btn_list_packages.clicked.connect(self.on_list_packages)
        self.btn_write_cmd.clicked.connect(self.on_write_cmd)
        self.btn_refresh_traces.clicked.connect(self.on_refresh_traces)
        self.btn_choose_dir.clicked.connect(self.on_choose_dir)
        self.btn_pull.clicked.connect(self.on_pull_trace)
        self.device_table.itemSelectionChanged.connect(self.on_device_selected)
        self.pkg_list.itemClicked.connect(lambda it: self.package.setText(it.text()))

    # -------------------- actions --------------------
    def pick_uaft(self):
        filt = "Executables (*.exe);;All files (*)" if sys.platform.startswith("win") else "All files (*)"
        path, _ = QFileDialog.getOpenFileName(self, "Select UnrealAndroidFileTool", "", filt)
        if path:
            self.uaft_path.setText(path)

    def pick_insights(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select UnrealInsights", "", "Executables (*)")
        if path:
            self.insights_path.setText(path)

    def on_list_devices(self):
        try:
            uaft = self._require_uaft()
            devs = uaft.devices()
            self.device_table.setRowCount(0)
            for d in devs:
                # fetch human-readable make/model using adb
                make, model = self._adb_device_info(d)
                row = self.device_table.rowCount()
                self.device_table.insertRow(row)
                self.device_table.setItem(row, 0, QTableWidgetItem(make))
                self.device_table.setItem(row, 1, QTableWidgetItem(model))
                self.device_table.setItem(row, 2, QTableWidgetItem(d))
            if devs:
                self.device_table.selectRow(0)
                self.serial.setText(devs[0])
            self._log(f"Found {len(devs)} device(s)")
        except Exception as e:
            if "UnrealAndroidFileTool" in str(e) or "valid UnrealAndroidFileTool path" in str(e):
                self._err("Pick UnrealAndroidFileTool.exe first (Tool Paths → Browse UAFT…) then try again.")
            else:
                self._err(e)
        except Exception as e:
            # Friendlier message if UAFT is missing
            if "UnrealAndroidFileTool" in str(e) or "valid UnrealAndroidFileTool path" in str(e):
                self._err("Pick UnrealAndroidFileTool.exe first (Tool Paths → Browse UAFT…) then try again.")
            else:
                self._err(e)

    def on_list_packages(self):
        try:
            uaft = self._require_uaft()
            dev = self.serial.text().strip() or None
            pkgs = uaft.packages(dev)
            self.pkg_list.clear()
            for p in pkgs:
                self.pkg_list.addItem(QListWidgetItem(p))
            if pkgs:
                self.pkg_list.setCurrentRow(0)
                self.package.setText(pkgs[0])
            self._log(f"Found {len(pkgs)} package(s) with AFS")
        except Exception as e:
            if "UnrealAndroidFileTool" in str(e) or "valid UnrealAndroidFileTool path" in str(e):
                self._err("Pick UnrealAndroidFileTool.exe first (Tool Paths → Browse UAFT…) then try again.")
            else:
                self._err(e)

    def on_device_selected(self):
        row = self.device_table.currentRow()
        if row >= 0:
            serial = self.device_table.item(row, 2).text()
            self.serial.setText(serial)

    def _adb_device_info(self, serial:str):
        try:
            code, out, err = run(["adb", "-s", serial, "shell", "getprop", "ro.product.manufacturer"])
            make = out.strip() if code == 0 else "?"
            code, out, err = run(["adb", "-s", serial, "shell", "getprop", "ro.product.model"])
            model = out.strip() if code == 0 else serial
            return make, model
        except Exception:
            return "?", serial

    def on_write_cmd(self):
        try:
            uaft = self._require_uaft()
            serial = self.serial.text().strip() or None
            ip = None if serial else (self.ip.text().strip() or None)
            port = self.port.text().strip() or None
            pkg = self.package.text().strip()
            token = self.security_token.text().strip() or None
            if not pkg:
                raise RuntimeError("Package is required")
            if not self._valid_package(pkg):
                raise RuntimeError("Package looks invalid. Use Android package format like 'com.company.game' (no ':' or spaces)")

            # Create a temp UECommandLine.txt
            content = self.trace_args.toPlainText().strip()
            if not content:
                raise RuntimeError("Please enter trace arguments to write to UECommandLine.txt")
            tmp = Path(Path.home()/"UECommandLine.txt")
            tmp.write_text(content, encoding="utf-8")
            out = uaft.push_commandfile(serial, ip, port, pkg, token, str(tmp))
            self._log("Pushed UECommandLine.txt to ^commandfile\n" + out)
        except Exception as e:
            self._err(e)

    def on_refresh_traces(self):
        try:
            uaft = self._require_uaft()
            serial = self.serial.text().strip() or None
            ip = None if serial else (self.ip.text().strip() or None)
            port = self.port.text().strip() or None
            pkg = self.package.text().strip()
            token = self.security_token.text().strip() or None
            traces = uaft.list_traces(serial, ip, port, pkg, token)
            self.trace_list.clear()
            for f in traces:
                self.trace_list.addItem(QListWidgetItem(f))
            self._log(f"Found {len(traces)} trace(s) under ^saved/Traces")
        except Exception as e:
            self._err(e)

    def on_choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Choose destination folder", self.pull_dir.text())
        if d:
            self.pull_dir.setText(d)

    def on_pull_trace(self):
        try:
            it = self.trace_list.currentItem()
            if not it:
                raise RuntimeError("Select a trace in the list first")
            remote_path = it.text()
            uaft = self._require_uaft()
            serial = self.serial.text().strip() or None
            ip = None if serial else (self.ip.text().strip() or None)
            port = self.port.text().strip() or None
            pkg = self.package.text().strip()
            token = self.security_token.text().strip() or None
            dest = Path(self.pull_dir.text().strip())
            local = uaft.pull_trace(serial, ip, port, pkg, token, remote_path, dest)
            self._log(f"Pulled {remote_path} -> {local}")
            if self.chk_open_insights.isChecked() and self.insights_path.text().strip():
                self._open_insights(local)
        except Exception as e:
            self._err(e)

    def _open_insights(self, trace_path:Path):
        exe = Path(self.insights_path.text().strip())
        if not exe.exists():
            self._err("UnrealInsights.exe not found")
            return
        try:
            subprocess.Popen([str(exe), str(trace_path)], shell=False)
            self._log("Launched Unreal Insights")
        except Exception as e:
            self._err(e)

    def _require_uaft(self) -> UAFT:
        p = Path(self.uaft_path.text().strip())
        if not p.exists():
            raise RuntimeError("Pick UnrealAndroidFileTool.exe first (Tool Paths → Browse UAFT…). It's usually at Engine/Binaries/DotNET/Android/<platform>/UnrealAndroidFileTool.exe")
        if not p.is_file():
            raise RuntimeError("The selected UAFT path is a folder. Please select the UnrealAndroidFileTool executable (…/UnrealAndroidFileTool.exe)")
        if sys.platform.startswith("win") and p.suffix.lower() != ".exe":
            self._log("Warning: UAFT on Windows should be an .exe — make sure you picked UnrealAndroidFileTool.exe")
        return UAFT(p)

    def _valid_package(self, pkg:str) -> bool:
        # Very simple Android package validation: segments separated by '.', no spaces/colons
        import re
        return bool(re.fullmatch(r"[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)+", pkg))

    def _log(self, msg:str):
        self.log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    def _err(self, e:Exception|str):
        text = str(e)
        self.log.append(f"<span style='color:#b00;'>Error: {text}</span>")
        QMessageBox.critical(self, "Error", text)


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        w = App(); w.show()
        sys.exit(app.exec())
    except Exception as e:
        # Last‑chance friendly error box if something fails before UI comes up
        try:
            QMessageBox.critical(None, "Startup Error", str(e))
        except Exception:
            pass
        raise

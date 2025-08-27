import hashlib
import os
import shutil
import socket
import subprocess
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

ADDONS_DIR = Path("/data/addons")
PROXY_DIR = Path("/opt/proxy/granturismo")
SYSTEMD_UNIT_PATH = Path("/etc/systemd/system/simdash-proxy@granturismo.service")


@dataclass
class InstallResult:
    ok: bool
    message: str


def _ensure_dirs() -> None:
    ADDONS_DIR.mkdir(parents=True, exist_ok=True)
    PROXY_DIR.mkdir(parents=True, exist_ok=True)


def _download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_tgz(tgz_path: Path, target_dir: Path) -> None:
    with tarfile.open(tgz_path, "r:*") as tf:
        tf.extractall(target_dir)


def _find_proxy_exec(base: Path) -> Optional[Path]:
    """
    Expect convention:
      /opt/proxy/granturismo/bin/proxy  (executable)
    If a versioned folder exists, allow /opt/proxy/granturismo/<ver>/bin/proxy
    """
    cand = base / "bin" / "proxy"
    if cand.exists() and os.access(cand, os.X_OK):
        return cand
    # search one level deep
    for sub in base.iterdir():
        if sub.is_dir():
            cand2 = sub / "bin" / "proxy"
            if cand2.exists() and os.access(cand2, os.X_OK):
                return cand2
    return None


def _write_systemd_unit(exec_path: Path) -> None:
    unit = f"""[Unit]
Description=SimDash Telemetry Proxy (granturismo) for PS5 %i
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=proxy
Group=proxy
ExecStart={exec_path} --ps5-ip %i --out-host 127.0.0.1 --out-port 5600
Restart=on-failure
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/simdash-proxy
CapabilityBoundingSet=
AmbientCapabilities=

[Install]
WantedBy=multi-user.target
"""
    SYSTEMD_UNIT_PATH.write_text(unit)


def _systemctl(*args: str) -> Tuple[bool, str]:
    try:
        out = subprocess.check_output(
            ["/bin/systemctl", *args], stderr=subprocess.STDOUT, text=True
        )
        return True, out.strip()
    except subprocess.CalledProcessError as e:
        return False, e.output.strip()


def _require_root() -> Optional[str]:
    try:
        return None if os.geteuid() == 0 else "Installer needs root privileges."
    except AttributeError:
        # Windows (not relevant on Pi), assume ok
        return None


def _ensure_proxy_user() -> None:
    # create 'proxy' user/group if missing
    subprocess.call(
        ["/usr/sbin/groupadd", "-r", "proxy"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.call(
        ["/usr/sbin/useradd", "-r", "-s", "/usr/sbin/nologin", "-g", "proxy", "proxy"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    Path("/var/lib/simdash-proxy").mkdir(parents=True, exist_ok=True)
    try:
        subprocess.call(
            ["/bin/chown", "-R", "proxy:proxy", "/var/lib/simdash-proxy"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def install_from_url(
    url: str, ps5_ip: str, sha256: Optional[str] = None
) -> InstallResult:
    # Basic IP sanity
    try:
        socket.inet_aton(ps5_ip)
    except OSError:
        return InstallResult(False, f"Invalid PS5 IP: {ps5_ip}")

    need_root = _require_root()
    if need_root:
        return InstallResult(False, need_root)

    _ensure_dirs()

    # download to /data/addons/granturismo-<ts>.tgz
    with tempfile.TemporaryDirectory(dir=str(ADDONS_DIR)) as tmpd:
        tmp = Path(tmpd)
        tgz_path = tmp / "proxy.tgz"
        try:
            _download(url, tgz_path)
        except Exception as e:
            return InstallResult(False, f"Download failed: {e}")

        if sha256:
            calc = _sha256(tgz_path)
            if calc.lower() != sha256.lower():
                return InstallResult(
                    False, f"SHA256 mismatch:\n expected {sha256}\n   actual {calc}"
                )

        # extract into /opt/proxy/granturismo (clean old)
        try:
            if PROXY_DIR.exists():
                # keep a backup if you want; for now replace
                shutil.rmtree(PROXY_DIR)
            PROXY_DIR.mkdir(parents=True, exist_ok=True)
            _extract_tgz(tgz_path, PROXY_DIR)
        except Exception as e:
            return InstallResult(False, f"Extract failed: {e}")

    exec_path = _find_proxy_exec(PROXY_DIR)
    if not exec_path:
        return InstallResult(
            False, "proxy executable not found under /opt/proxy/granturismo/bin/proxy"
        )

    # systemd bits
    try:
        _ensure_proxy_user()
        _write_systemd_unit(exec_path)
        _systemctl("daemon-reload")
        ok, out = _systemctl("enable", f"simdash-proxy@{ps5_ip}.service")
        if not ok:
            return InstallResult(False, f"systemctl enable failed: {out}")
        ok, out = _systemctl("restart", f"simdash-proxy@{ps5_ip}.service")
        if not ok:
            return InstallResult(False, f"systemctl start failed: {out}")
    except Exception as e:
        return InstallResult(False, f"systemd setup failed: {e}")

    return InstallResult(True, f"Installed and started proxy for {ps5_ip}")

"""The bench's parts: radios, medium, access points, client, recorder.

One run of the bench builds everything from nothing and removes it afterwards:
mac80211_hwsim is loaded with the radios the run needs, each radio is moved into
its network namespace (ap1, ap2, sta), the distribution system is a bridge in
namespace ds, wmediumd carries every frame, hostapd runs each access point and
the client runs in sta. Everything is recorded in one timeline on one clock.
Standard library only; runs as root.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

RUN = Path("/run/bench")
NOISE_DBM = -91          # the medium reports signal = SNR + this
ABSENT_DBM = -110        # a level that no frame survives
SSID = "bench"
PSK = "bench-passphrase"
SERVER = "10.99.0.1"
CLIENT = "10.99.0.2"
NAMESPACES = ("ap1", "ap2", "sta", "ds")
CHANNELS = {"5": (36, 5180, "a", 115), "2.4": (1, 2412, "g", 81)}
IWD_KNOWN_FREQUENCIES = "5180 2412"
# A bus for iwd alone, so nothing is installed on the host
DBUS_CONF = """<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>system</type>
  <listen>unix:path={socket}</listen>
  <auth>EXTERNAL</auth>
  <policy context="default">
    <allow user="*"/>
    <allow own="*"/>
    <allow send_destination="*"/>
    <allow receive_sender="*"/>
  </policy>
</busconfig>
"""


class BenchError(RuntimeError):
    pass


def run(args: list[str], ns: str | None = None, check: bool = True, timeout: float = 30,
        capture: bool = True) -> subprocess.CompletedProcess:
    cmd = (["ip", "netns", "exec", ns] if ns else []) + [str(a) for a in args]
    result = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
    if check and result.returncode:
        raise BenchError(f"{' '.join(cmd)}: exit {result.returncode}: "
                         f"{(result.stderr or result.stdout or '').strip()}")
    return result


# --- the control interface of hostapd and wpa_supplicant (the wpa_ctrl protocol)

class Ctrl:
    _count = 0
    _lock = threading.Lock()

    def __init__(self, path: Path | str, timeout: float = 5):
        with Ctrl._lock:
            Ctrl._count += 1
            n = Ctrl._count
        self.local = RUN / f"ctrl-{os.getpid()}-{n}"
        self.local.unlink(missing_ok=True)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.sock.bind(str(self.local))
        self.sock.connect(str(path))
        self.sock.settimeout(timeout)
        self.attached = False
        self.lock = threading.Lock()

    def request(self, command: str, timeout: float = 5) -> str:
        with self.lock:
            self.sock.settimeout(timeout)
            self.sock.send(command.encode())
            while True:
                reply = self.sock.recv(65536).decode(errors="replace")
                if self.attached and reply.startswith("<"):
                    continue  # an event on a monitor socket
                return reply

    def attach(self) -> None:
        if self.request("ATTACH").strip() != "OK":
            raise BenchError("ATTACH failed")
        self.attached = True

    def event(self, timeout: float) -> str | None:
        self.sock.settimeout(timeout)
        try:
            return self.sock.recv(65536).decode(errors="replace")
        except (socket.timeout, TimeoutError):
            return None

    def close(self) -> None:
        try:
            if self.attached:
                self.sock.send(b"DETACH")
        except OSError:
            pass
        self.sock.close()
        self.local.unlink(missing_ok=True)


def wait_ctrl(path: Path, timeout: float = 10) -> Ctrl:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            try:
                c = Ctrl(path)
                if c.request("PING").strip() == "PONG":
                    return c
                c.close()
            except OSError:
                pass
        time.sleep(0.1)
    raise BenchError(f"no control interface at {path}")


def kv(text: str) -> dict:
    return dict(line.split("=", 1) for line in text.splitlines() if "=" in line)


# --- the timeline

class Timeline:
    def __init__(self, path: Path):
        self.t0 = time.monotonic()
        self.lock = threading.Lock()
        self.records: list[dict] = []
        self.file = path.open("w")

    def now(self) -> float:
        return round(time.monotonic() - self.t0, 3)

    def add(self, source: str, kind: str, **fields) -> dict:
        record = {"t": self.now(), "source": source, "kind": kind, **fields}
        with self.lock:
            self.records.append(record)
            self.file.write(json.dumps(record) + "\n")
            self.file.flush()
        return record

    def since(self, t: float) -> list[dict]:
        with self.lock:
            return [r for r in self.records if r["t"] >= t]

    def close(self) -> None:
        self.file.close()


EVENT_NAME = re.compile(r"^(?:<\d>)?(\S+)")


class Listener(threading.Thread):
    """Records every event of one control interface."""

    def __init__(self, timeline: Timeline, source: str, path: Path):
        super().__init__(daemon=True)
        self.timeline, self.source, self.path = timeline, source, path
        self.stop = threading.Event()
        self.ctrl = Ctrl(path)
        self.ctrl.attach()

    def run(self) -> None:
        while not self.stop.is_set():
            try:
                text = self.ctrl.event(0.5)
            except OSError:
                break
            if text:
                body = re.sub(r"^<\d>", "", text.strip())
                name = EVENT_NAME.match(body).group(1)
                self.timeline.add(self.source, "event", name=name, text=body)

    def close(self) -> None:
        self.stop.set()
        self.join(2)
        self.ctrl.close()


class Poller(threading.Thread):
    """The client's state every second: BSSID, frequency and levels."""

    def __init__(self, timeline: Timeline, sample, interval: float = 1.0):
        super().__init__(daemon=True)
        self.timeline, self.sample, self.interval = timeline, sample, interval
        self.stop = threading.Event()

    def run(self) -> None:
        while not self.stop.wait(self.interval):
            try:
                self.timeline.add("client", "poll", **self.sample())
            except Exception as e:  # the client may be restarting
                self.timeline.add("client", "poll-error", error=str(e))

    def close(self) -> None:
        self.stop.set()
        self.join(3)


# --- the medium

class Medium:
    """wmediumd with its control socket; levels set as directed SNR, both ways."""

    def __init__(self, wmediumd: Path, medium_checkout: Path, radios: dict[str, str],
                 levels: dict[tuple[str, str], int], workdir: Path):
        self.radios = radios  # name -> the address wmediumd knows the radio by
        self.names = list(radios)
        config = workdir / "wmediumd.cfg"
        links = []
        for (a, b), level in levels.items():
            i, j = self.names.index(a), self.names.index(b)
            links += [(i, j, level - NOISE_DBM), (j, i, level - NOISE_DBM)]
        config.write_text(
            "ifaces : {\n  ids = [\n"
            + ",\n".join(f'    "{radios[n]}"' for n in self.names)
            + "\n  ];\n};\nmodel : {\n  type = \"snr\";\n"
            + f"  default_snr = {ABSENT_DBM - NOISE_DBM};\n  links = (\n"
            + ",\n".join(f"    ({i}, {j}, {s})" for i, j, s in links)
            + "\n  );\n};\n")
        self.control = RUN / "wmediumd-control.sock"
        self.control.unlink(missing_ok=True)
        self.log = (workdir / "wmediumd.log").open("w")
        self.proc = subprocess.Popen([str(wmediumd), "-l", "5", "-c", str(config),
                                      "-C", str(self.control)],
                                     stdout=self.log, stderr=subprocess.STDOUT)
        (RUN / "wmediumd.pid").write_text(str(self.proc.pid))
        sys.path.insert(0, str(medium_checkout / "configurator"))
        from wmdcfg.actuator import ControlClient  # noqa: E402 (the medium's own client)
        deadline = time.monotonic() + 10
        while not self.control.exists():
            if self.proc.poll() is not None or time.monotonic() > deadline:
                raise BenchError("wmediumd did not start; see wmediumd.log")
            time.sleep(0.1)
        self.client = ControlClient(str(self.control))
        self.generation = self.client.connect().generation
        self.levels = dict(levels)

    def set(self, levels: dict[tuple[str, str], int]) -> int:
        updates = []
        for (a, b), level in levels.items():
            snr = max(-127, min(127, level - NOISE_DBM))
            updates += [{"source": self.radios[a], "destination": self.radios[b], "value": snr},
                        {"source": self.radios[b], "destination": self.radios[a], "value": snr}]
            self.levels[(a, b)] = level
        self.generation += 1
        self.client.apply(self.generation, updates)
        return self.generation

    def close(self) -> None:
        try:
            self.client.close()
        except Exception:
            pass
        self.proc.terminate()
        try:
            self.proc.wait(5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
        self.log.close()


# --- radios and namespaces

def teardown() -> None:
    for name in ("hostapd", "wpa_supplicant", "iwd", "dbus-daemon", "wmediumd"):
        pidfiles = list(RUN.glob(f"{name}*.pid")) if RUN.exists() else []
        for pidfile in pidfiles:
            try:
                os.kill(int(pidfile.read_text().strip()), 15)
            except (ValueError, ProcessLookupError, PermissionError):
                pass
            pidfile.unlink(missing_ok=True)
    # stale control sockets would answer for a client that is not running
    if RUN.exists():
        for d in [RUN / "wpa", *RUN.glob("hostapd-*")]:
            if d.is_dir():
                shutil.rmtree(d, ignore_errors=True)
    existing = run(["ip", "netns", "list"]).stdout
    for ns in NAMESPACES:
        if re.search(rf"^{ns}\b", existing, re.M):
            run(["ip", "netns", "delete", ns], check=False)
    for _ in range(50):
        if run(["rmmod", "mac80211_hwsim"], check=False).returncode == 0 or \
                not Path("/sys/module/mac80211_hwsim").exists():
            break
        time.sleep(0.2)


def phys() -> list[str]:
    names = [p.name for p in Path("/sys/class/ieee80211").iterdir()]
    return sorted(names, key=lambda n: int(n[3:]))


def hw_address(perm: str) -> str:
    """wmediumd knows a radio by the transmitter address hwsim puts on its
    frames: the permanent address with 0x40 set in its first byte."""
    return f"{int(perm[:2], 16) | 0x40:02x}{perm[2:]}"


def iface_of(phy_index: int, ns: str) -> str:
    out = run(["iw", "dev"], ns=ns).stdout
    current = None
    for line in out.splitlines():
        m = re.match(r"phy#(\d+)", line.strip())
        if m:
            current = int(m.group(1))
        m = re.match(r"\s*Interface (\S+)", line)
        if m and current == phy_index:
            return m.group(1)
    raise BenchError(f"no interface of phy{phy_index} in {ns}")


class Rig:
    """The bench for one run: radios, namespaces, medium, access points."""

    def __init__(self, build: Path, wmediumd: Path, medium: Path, workdir: Path,
                 bands: tuple[str, ...] = ("5",), load: dict | None = None,
                 levels: dict[str, int] | None = None):
        self.build, self.workdir = build, workdir
        self.bands = bands
        # the access points of the run's first band, which the walks move
        self.ap1, self.ap2 = f"ap1-{bands[0]}", f"ap2-{bands[0]}"
        self.load = load or {}
        self.procs: list[subprocess.Popen] = []
        self.client_kind: str | None = None
        self.listeners: list[Listener] = []
        self.poller: Poller | None = None
        teardown()
        RUN.mkdir(parents=True, exist_ok=True)
        workdir.mkdir(parents=True, exist_ok=True)
        # radio order: per band ap1, ap2; then the client
        roles = [f"{ap}-{b}" for b in bands for ap in ("ap1", "ap2")] + ["sta"]
        run(["modprobe", "mac80211_hwsim", f"radios={len(roles)}"])
        run(["iw", "reg", "set", "US"])
        found = phys()[-len(roles):]
        self.phy = dict(zip(roles, found))
        self.addr = {r: Path(f"/sys/class/ieee80211/{p}/macaddress").read_text().strip()
                     for r, p in self.phy.items()}
        for ns in NAMESPACES:
            run(["ip", "netns", "add", ns])
        run(["ip", "link", "add", "br-ds", "type", "bridge"], ns="ds")
        run(["ip", "addr", "add", f"{SERVER}/24", "dev", "br-ds"], ns="ds")
        run(["ip", "link", "set", "br-ds", "up"], ns="ds")
        run(["ip", "link", "set", "lo", "up"], ns="ds")
        for ap in ("ap1", "ap2"):
            run(["ip", "link", "add", f"v-{ap}", "netns", ap, "type", "veth", "peer", "name",
                 f"v-{ap}-ds", "netns", "ds"])
            run(["ip", "link", "add", "br0", "type", "bridge"], ns=ap)
            run(["ip", "link", "set", f"v-{ap}", "master", "br0"], ns=ap)
            for link in ("br0", f"v-{ap}"):
                run(["ip", "link", "set", link, "up"], ns=ap)
            run(["ip", "link", "set", f"v-{ap}-ds", "master", "br-ds"], ns="ds")
            run(["ip", "link", "set", f"v-{ap}-ds", "up"], ns="ds")
        for role, phy in self.phy.items():
            run(["iw", "phy", phy, "set", "netns", "name", role.split("-")[0]])
        self.iface = {role: iface_of(int(phy[3:]), role.split("-")[0])
                      for role, phy in self.phy.items()}
        run(["ip", "link", "set", "lo", "up"], ns="sta")
        run(["ip", "addr", "add", f"{CLIENT}/24", "dev", self.iface["sta"]], ns="sta")

        radios = {role: hw_address(perm) for role, perm in self.addr.items()}
        initial = {}
        levels = levels or {}
        for role in roles[:-1]:
            initial[(role, "sta")] = levels.get(role, ABSENT_DBM)
        for b in bands:
            initial[(f"ap1-{b}", f"ap2-{b}")] = -60
        self.medium = Medium(wmediumd, medium, radios, initial, workdir)
        self.timeline = Timeline(workdir / "timeline.jsonl")
        self.timeline.add("driver", "rig", phys=self.phy, addresses=self.addr, bands=list(bands),
                          load=self.load)
        self.record_levels("initial")
        for role in roles[:-1]:
            self.start_ap(role)
        self.set_neighbors(roles[:-1])

    # access points
    def start_ap(self, role: str) -> None:
        ap, band = role.split("-")
        channel, _, hw_mode, _ = CHANNELS[band]
        ctrl_dir = RUN / f"hostapd-{role}"
        lines = [
            f"interface={self.iface[role]}", "driver=nl80211", f"ctrl_interface={ctrl_dir}",
            f"ssid={SSID}", "country_code=US", f"hw_mode={hw_mode}", f"channel={channel}",
            "wpa=2", "wpa_key_mgmt=WPA-PSK", "rsn_pairwise=CCMP", f"wpa_passphrase={PSK}",
            "bridge=br0", "bss_transition=1", "rrm_neighbor_report=1",
        ]
        if role in self.load:
            # Station Count : Channel Utilization (of 255) : Available Admission Capacity
            lines.append(f"bss_load_test=1:{round(self.load[role] * 255 / 100)}:0")
        conf = self.workdir / f"hostapd-{role}.conf"
        conf.write_text("\n".join(lines) + "\n")
        pidfile = RUN / f"hostapd-{role}.pid"
        run([self.build / "hostapd", "-B", "-t", "-d", "-f", self.workdir / f"hostapd-{role}.log",
             "-P", pidfile, conf], ns=ap)
        path = ctrl_dir / self.iface[role]
        c = wait_ctrl(path)
        deadline = time.monotonic() + 15
        while kv(c.request("STATUS")).get("state") != "ENABLED":
            if time.monotonic() > deadline:
                raise BenchError(f"{role} did not come up; see hostapd-{role}.log")
            time.sleep(0.2)
        c.close()
        self.listeners.append(Listener(self.timeline, role, path))
        self.listeners[-1].start()

    def set_neighbors(self, roles: list[str]) -> None:
        """Each AP lists the other AP of its band in its 802.11k neighbor
        report, as an AP that offers neighbor reports does (hostapd's own
        list holds only itself)."""
        for role in roles:
            ap, band = role.split("-")
            other = f"{'ap2' if ap == 'ap1' else 'ap1'}-{band}"
            if other not in roles:
                continue
            channel, _, _, op_class = CHANNELS[band]
            phy_type = 4 if channel > 14 else 6  # OFDM (802.11a) or ERP (802.11g)
            # BSSID, BSSID Information (reachable, security, key scope),
            # Operating Class, Channel, PHY type
            nr = (self.addr[other].replace(":", "") + "0f000000"
                  + f"{op_class:02x}{channel:02x}{phy_type:02x}")
            c = self.ap_ctrl(role)
            try:
                reply = c.request(f'SET_NEIGHBOR {self.addr[other]} ssid="{SSID}" nr={nr}').strip()
            finally:
                c.close()
            if reply != "OK":
                raise BenchError(f"{role}: SET_NEIGHBOR failed: {reply}")
        self.timeline.add("driver", "neighbors", roles=roles)

    def ap_ctrl(self, role: str) -> Ctrl:
        return Ctrl(RUN / f"hostapd-{role}" / self.iface[role])

    def bssid(self, role: str) -> str:
        return self.addr[role]

    # levels
    def record_levels(self, why: str, generation: int | None = None) -> None:
        self.timeline.add("driver", "levels", why=why, generation=generation,
                          levels={a: v for (a, b), v in self.medium.levels.items() if b == "sta"})

    def set_levels(self, levels: dict[str, int], why: str = "walk") -> None:
        generation = self.medium.set({(role, "sta"): v for role, v in levels.items()})
        self.record_levels(why, generation)

    def level_at(self, role: str, t: float) -> int | None:
        value = None
        for r in self.timeline.records:
            if r["t"] > t:
                break
            if r["kind"] == "levels":
                value = r["levels"].get(role, value)
        return value

    # the client
    def start_wpa(self, conf_text: str, binary: str = "wpa_supplicant") -> None:
        self.client_kind = "wpa_supplicant"
        conf = self.workdir / "client.conf"
        conf.write_text(conf_text)
        # In the foreground, its debug output into client.log: this works with any
        # build, including the RDK lab's 2.10, which has no CONFIG_DEBUG_FILE for -f
        log_path = self.workdir / "client.log"
        log = log_path.open("w")
        proc = subprocess.Popen(["ip", "netns", "exec", "sta", str(self.build / binary), "-t", "-d",
                                 "-D", "nl80211", "-i", self.iface["sta"], "-c", str(conf)],
                                stdout=log, stderr=subprocess.STDOUT)
        log.close()
        (RUN / "wpa_supplicant.pid").write_text(str(proc.pid))
        self.procs.append(proc)
        path = RUN / "wpa" / self.iface["sta"]
        deadline = time.monotonic() + 10
        while True:
            if proc.poll() is not None:
                tail = log_path.read_text().strip().splitlines()[-3:]
                raise BenchError(f"{binary} exited ({proc.returncode}): {' | '.join(tail)}")
            try:
                wait_ctrl(path, timeout=0.5).close()
                break
            except BenchError:
                if time.monotonic() > deadline:
                    raise
        self.client_ctrl = Ctrl(path)
        self.listeners.append(Listener(self.timeline, "client", path))
        self.listeners[-1].start()

        def sample() -> dict:
            status = kv(self.client_ctrl.request("STATUS"))
            poll = kv(self.client_ctrl.request("SIGNAL_POLL"))
            return {"state": status.get("wpa_state"), "bssid": status.get("bssid"),
                    "freq": int(status["freq"]) if "freq" in status else None,
                    "rssi": int(poll["RSSI"]) if "RSSI" in poll else None,
                    "avg_rssi": int(poll["AVG_RSSI"]) if "AVG_RSSI" in poll else None,
                    "beacon_rssi": int(poll["AVG_BEACON_RSSI"]) if "AVG_BEACON_RSSI" in poll else None}
        self.poller = Poller(self.timeline, sample)
        self.poller.start()

    def start_iwd(self, main_conf: str, iwd: Path) -> None:
        """iwd in namespace sta, on a D-Bus of its own; its state polled through iw."""
        self.client_kind = "iwd"
        state = self.workdir / "iwd-state"
        conf_dir = self.workdir / "iwd-conf"
        for d in (state, conf_dir):
            shutil.rmtree(d, ignore_errors=True)
            d.mkdir(parents=True)
        (conf_dir / "main.conf").write_text(main_conf)
        (state / f"{SSID}.psk").write_text(f"[Security]\nPassphrase={PSK}\n\n[Settings]\nAutoConnect=true\n")
        # The bench's environment, as freq_list is for wpa_supplicant: iwd's own
        # record of where it has seen the network, so its quick scans cover the
        # bench's two channels instead of a passive scan of every channel
        (state / ".known_network.freq").write_text(
            f"[6f1c1c52-8a43-4f0e-9d39-1f0b6a5c2e11]\nname={state / (SSID + '.psk')}\n"
            f"list={IWD_KNOWN_FREQUENCIES}\n")
        bus = RUN / "dbus.sock"
        bus.unlink(missing_ok=True)
        (self.workdir / "dbus.conf").write_text(DBUS_CONF.format(socket=bus))
        dbus = subprocess.Popen(["dbus-daemon", "--nofork", "--nopidfile",
                                 f"--config-file={self.workdir / 'dbus.conf'}"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        (RUN / "dbus-daemon.pid").write_text(str(dbus.pid))
        self.procs.append(dbus)
        deadline = time.monotonic() + 5
        while not bus.exists():
            if time.monotonic() > deadline:
                raise BenchError("the bench's D-Bus did not start")
            time.sleep(0.1)
        env = dict(os.environ, STATE_DIRECTORY=str(state), CONFIGURATION_DIRECTORY=str(conf_dir),
                   DBUS_SYSTEM_BUS_ADDRESS=f"unix:path={bus}")
        log = (self.workdir / "client.log").open("w")
        proc = subprocess.Popen(["ip", "netns", "exec", "sta", str(iwd), "-d", "-i", self.iface["sta"]],
                                stdout=log, stderr=subprocess.STDOUT, env=env)
        (RUN / "iwd.pid").write_text(str(proc.pid))
        self.procs.append(proc)
        threading.Thread(target=self._follow_log, args=(self.workdir / "client.log",), daemon=True).start()

        def sample() -> dict:
            out = run(["iw", "dev", self.iface["sta"], "link"], ns="sta", check=False).stdout
            m = re.search(r"Connected to (\S+)", out)
            sig = re.search(r"signal: (-?\d+)", out)
            freq = re.search(r"freq: (\d+)", out)
            return {"state": "COMPLETED" if m else "DISCONNECTED", "bssid": m.group(1) if m else None,
                    "freq": int(freq.group(1)) if freq else None,
                    "rssi": int(sig.group(1)) if sig else None}
        self.poller = Poller(self.timeline, sample)
        self.poller.start()

    def _follow_log(self, path: Path) -> None:
        """iwd has no control socket: its debug lines about roaming become events."""
        with path.open() as f:
            while True:
                line = f.readline()
                if not line:
                    if self.poller and self.poller.stop.is_set():
                        return
                    time.sleep(0.2)
                    continue
                if re.search(r"roam|Roam|cqm|CQM|neighbor report|scan_triggered|Connected|"
                             r"bss.transition|BSS Transition", line):
                    self.timeline.add("client", "iwd", text=line.strip())

    def client_request(self, command: str) -> str:
        return self.client_ctrl.request(command)

    # traffic
    def ping(self, count: int = 3) -> bool:
        return run(["ping", "-c", count, "-W", "2", SERVER], ns="sta", check=False,
                   timeout=count * 3 + 5).returncode == 0

    def start_traffic(self, interval: float = 0.02) -> subprocess.Popen:
        p = subprocess.Popen(["ip", "netns", "exec", "sta", "ping", "-q", "-i", str(interval), SERVER],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.procs.append(p)
        return p

    def stop_traffic(self, p: subprocess.Popen) -> str:
        p.send_signal(2)
        try:
            out, _ = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            out, _ = p.communicate()
        return out.strip().splitlines()[-2] if out.strip() else ""

    def close(self) -> None:
        if self.poller:
            self.poller.close()
        for listener in self.listeners:
            listener.close()
        if hasattr(self, "client_ctrl"):
            self.client_ctrl.close()
        for p in self.procs:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(5)
                except subprocess.TimeoutExpired:
                    p.kill()
        self.timeline.close()
        self.medium.close()
        teardown()

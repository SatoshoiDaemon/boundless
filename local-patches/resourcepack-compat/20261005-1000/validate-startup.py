from pathlib import Path
import json
import os
import signal
import subprocess
import time
import shutil

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent / "validation"
OUT.mkdir(exist_ok=True)
options = ROOT / "options.txt"
before = options.read_bytes()
(OUT / "options-before-startup.txt").write_bytes(before)
lines = before.decode().splitlines()
lines = ["maxFps:30" if x.startswith("maxFps:") else x for x in lines]
options.write_text("\n".join(lines) + "\n")

def game_pids():
    found = []
    for p in Path("/proc").iterdir():
        if not p.name.isdigit():
            continue
        try:
            args = (p / "cmdline").read_bytes().split(b"\0")
            if ((p / "comm").read_text().strip() == "java"
                    and (p / "cwd").resolve() == ROOT
                    and b"org.prismlauncher.EntryPoint" in args):
                found.append(int(p.name))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return found

def cpu_temp():
    values = []
    for hw in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (hw / "name").read_text().strip() in ("coretemp", "k10temp", "cpu_thermal"):
                values.extend(int(x.read_text()) / 1000 for x in hw.glob("temp*_input"))
        except (FileNotFoundError, PermissionError, ValueError):
            pass
    return max(values, default=0)

existing = set(game_pids())
started = set()
result = {"status": "pending", "max_cpu_temp": 0, "test": "menu resource reload only; no world opened"}
began = time.time()
menu_at = None
last_report = 0
try:
    assert not existing, "Minecraft already running"
    with (OUT / "launcher-output.log").open("w") as output:
        launcher = subprocess.Popen(["freesmlauncher", "--launch", "1.20.1", "--offline", "TextureAudit"], stdout=output, stderr=subprocess.STDOUT)
    while time.time() - began < 240:
        current = set(game_pids()) - existing
        new = current - started
        if new:
            print("Minecraft de teste iniciado; carregando recursos.", flush=True)
        started.update(current)
        # Keep the validation's CPU load bounded without changing user settings.
        allowed = sorted(os.sched_getaffinity(0))[:4]
        for pid in current:
            for thread in (Path("/proc") / str(pid) / "task").glob("*"):
                try:
                    os.sched_setaffinity(int(thread.name), allowed)
                except (ProcessLookupError, PermissionError):
                    pass
        temp = cpu_temp()
        result["max_cpu_temp"] = max(result["max_cpu_temp"], temp)
        if temp >= 88:
            result["status"] = "temperature_cutoff"
            print("Teste encerrado pelo limite de temperatura.", flush=True)
            break
        latest = ROOT / "logs/latest.log"
        if latest.exists() and latest.stat().st_mtime >= began:
            text = latest.read_text(errors="replace")
            if "MAIN_MENU_" in text and menu_at is None:
                menu_at = time.time()
                print("Menu principal alcançado; conferindo fim do carregamento.", flush=True)
            if menu_at is not None and time.time() - menu_at >= 12:
                result["status"] = "main_menu_loaded"
                break
        if started and not current:
            result["status"] = "process_exited_before_menu"
            break
        if time.time() - last_report >= 30:
            print("Validação em andamento: %d s; CPU %.0f °C." % (time.time() - began, temp), flush=True)
            last_report = time.time()
        time.sleep(2)
    else:
        result["status"] = "startup_timeout"
finally:
    for pid in started & set(game_pids()):
        os.kill(pid, signal.SIGTERM)
    end = time.time() + 15
    while started & set(game_pids()) and time.time() < end:
        time.sleep(1)
    for pid in started & set(game_pids()):
        os.kill(pid, signal.SIGKILL)
    options.write_bytes(before)
    for name in ("latest.log", "debug.log"):
        source = ROOT / "logs" / name
        if source.exists():
            shutil.copy2(source, OUT / name)
    result["elapsed_seconds"] = round(time.time() - began)
    result["options_restored"] = options.read_bytes() == before
    (OUT / "startup-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)

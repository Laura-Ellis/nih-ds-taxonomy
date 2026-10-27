"""
Simple project task runner (Windows-friendly, no Anaconda).

Usage examples:
    python tasks.py create-venv
    python tasks.py install
    python tasks.py freeze
    python tasks.py jupyter
    python tasks.py info
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

VENV_DIR = Path(".venv")


def _run(cmd, cwd=None):
    print("+ " + " ".join(map(str, cmd)))
    subprocess.check_call(cmd, cwd=cwd)


def _venv_python():
    return VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _venv_pip():
    return VENV_DIR / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")


def task_create_venv(args):
    if VENV_DIR.exists():
        print("Virtual environment already exists.")
        return
    _run([sys.executable, "-m", "venv", str(VENV_DIR)])
    print("Virtual environment created!")
    print("Activate with:")
    print(r"  Windows (PowerShell): .venv\Scripts\Activate")
    print("  macOS / Linux:        source .venv/bin/activate")


def task_install(args):
    if not VENV_DIR.exists():
        print("No venv found. Run: python tasks.py create-venv")
        return
    pip = _venv_pip()
    _run([str(pip), "install", "--upgrade", "pip"])
    if Path("requirements.txt").exists():
        _run([str(pip), "install", "-r", "requirements.txt"])
    elif Path("requirements.template.txt").exists():
        print("requirements.txt not found; installing from requirements.template.txt")
        _run([str(pip), "install", "-r", "requirements.template.txt"])
    else:
        print("No requirements file found")


def task_freeze(args):
    if not VENV_DIR.exists():
        print("No venv found.")
        return
    pip = _venv_pip()
    with open("requirements.txt", "w") as f:
        subprocess.check_call([str(pip), "freeze"], stdout=f)
    print("requirements.txt updated.")


def task_jupyter(args):
    if not VENV_DIR.exists():
        print("No venv found.")
        return
    python = _venv_python()
    _run([str(python), "-m", "jupyter", "notebook"])


def task_info(args):
    print("System Python:", sys.executable)
    print("Venv Python:", _venv_python())
    print("Venv Pip:", _venv_pip())


def main():
    parser = argparse.ArgumentParser(description="Task runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for cmd in ["create-venv", "install", "freeze", "jupyter", "info"]:
        sp = subparsers.add_parser(cmd)
        sp.set_defaults(func=globals()[f"task_{cmd.replace('-', '_')}"])

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

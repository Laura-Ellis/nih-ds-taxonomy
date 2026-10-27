"""Progress messages for long notebook steps, so a run shows it's alive.

    from progress import step
    with step("Label project text with keywords"):
        ...  # prints a start line, a heartbeat every 60 seconds, and the time taken

    from progress import start
    stop = start("Combine text per project")   # same, without indenting a whole notebook cell
    ...
    stop()

Every line is flushed right away, so it shows up in a log file during the run, not only at the end.
"""

import threading
import time
from contextlib import contextmanager
from datetime import datetime

HEARTBEAT_SECONDS = 60


def say(message: str) -> None:
    """Print a time-stamped line and flush it immediately."""
    print(f"[{datetime.now():%H:%M:%S}] {message}", flush=True)


@contextmanager
def step(name: str, every: int = HEARTBEAT_SECONDS):
    """Wrap a long step: start line, heartbeat every `every` seconds, then the elapsed time."""
    t0, done = time.time(), threading.Event()

    def beat() -> None:
        while not done.wait(every):
            say(f"  ...still working on {name} ({(time.time() - t0) / 60:.0f} min so far)")

    say(f"Start: {name}")
    threading.Thread(target=beat, daemon=True).start()
    try:
        yield
    finally:
        done.set()
        say(f"Done: {name} ({time.time() - t0:.0f}s)")


def start(name: str, every: int = HEARTBEAT_SECONDS):
    """Like `step`, for a notebook cell you don't want to indent: returns a function to call when done.
    If the cell fails before that, the heartbeat thread stops with the program."""
    t0, done = time.time(), threading.Event()

    def beat() -> None:
        while not done.wait(every):
            say(f"  ...still working on {name} ({(time.time() - t0) / 60:.0f} min so far)")

    say(f"Start: {name}")
    threading.Thread(target=beat, daemon=True).start()

    def stop() -> None:
        done.set()
        say(f"Done: {name} ({time.time() - t0:.0f}s)")
    return stop

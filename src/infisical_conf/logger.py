# logger.py

import time
from rich import print as rprint


class _Logger:
    LEVELS = {
        "DEBUG":    10,
        "INFO":     20,
        "WARNING":  30,
        "ERROR":    40,
        "CRITICAL": 50,
    }

    STYLES = {
        "DEBUG":    "dim cyan",
        "INFO":     "green",
        "WARNING":  "yellow",
        "ERROR":    "bold red",
        "CRITICAL": "bold white on red",
    }

    def __init__(self, threshold="INFO", app_name="APP", method_width=20):
        self.set_threshold(threshold)
        self.app_name = app_name
        self.method_width = method_width

    def configure(self, *, app_name=None, method_width=None):
        if app_name:
            self.app_name = app_name
        if method_width:
            self.method_width = method_width

    def set_threshold(self, level_name):
        self.threshold = self.LEVELS.get(level_name.upper(), 20)

    def emit(self, method, msg, level="INFO"):
        level = level.upper()
        numeric = self.LEVELS.get(level, 20)

        if numeric < self.threshold:
            return

        timestamp = time.strftime("%H:%M:%S")
        sev_style = self.STYLES.get(level, "white")

        # METHOD always yellow
        method_style = "yellow"

        rprint(
            f"[dim][{timestamp}][/dim] | "
            f"[{sev_style}]{level:<8}[/{sev_style}] | "
            f"[bold blue]{self.app_name}[/bold blue] | "
            f"[{method_style}]{method:>{self.method_width}}[/{method_style}] | "
            f"{msg}"
        )


# Global logger instance
_LOGGER = _Logger("INFO")


def log(method, msg, level="INFO"):
    _LOGGER.emit(method, msg, level)


def set_log_level(level):
    _LOGGER.set_threshold(level)


def configure_logger(*, app_name=None, method_width=None):
    _LOGGER.configure(app_name=app_name, method_width=method_width)

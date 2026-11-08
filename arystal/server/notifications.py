"""macOS notifications for long jobs. Does nothing on other systems."""

import subprocess
import sys

# A job that takes at least this long (wall-clock seconds) triggers a notification when it ends.
DEFAULT_NOTIFY_AFTER_SECONDS = 60.0

NOTIFICATION_TIMEOUT_SECONDS = 5


def escape_for_applescript(text: str) -> str:
    """Return the text safe to place inside a double-quoted AppleScript string (backslashes and quotes escaped, line breaks removed)."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")


def build_notification_script(title: str, message: str) -> str:
    """Return the AppleScript that shows a notification."""
    return f'display notification "{escape_for_applescript(message)}" with title "{escape_for_applescript(title)}"'


def notify_macos(title: str, message: str) -> bool:
    """Show a macOS notification. Returns True if it was sent (False on other systems or if osascript failed)."""
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["osascript", "-e", build_notification_script(title, message)],
            capture_output=True, timeout=NOTIFICATION_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def should_notify(wall_seconds: float, threshold_seconds: float = DEFAULT_NOTIFY_AFTER_SECONDS) -> bool:
    """True if a job that took `wall_seconds` is long enough to deserve a notification."""
    return wall_seconds >= threshold_seconds

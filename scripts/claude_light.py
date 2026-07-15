#!/usr/bin/env python3
"""
Claude Code traffic light controller — WiFi edition.
Usage:
  claude_light.py THINKING   - chase animation (Claude reasoning)
  claude_light.py EXECUTING  - yellow solid (tool running)
  claude_light.py DONE       - green (auto-transitions to IDLE after 3s on ESP32)
  claude_light.py ERROR      - red solid
  claude_light.py IDLE       - all off
  claude_light.py hook-post  - read PostToolUse JSON from stdin, send ERROR or THINKING

ESP32 hostname: set CLAUDE_LIGHT_HOST env var, default: esp32-traffic-light.local
"""

import sys
import os
import urllib.request

# mDNS hostname or IP of the ESP32
WIFI_HOST = os.environ.get("CLAUDE_LIGHT_HOST", "esp32-traffic-light.local")


def send(state: str):
    try:
        url = f"http://{WIFI_HOST}/cmd?state={state}"
        urllib.request.urlopen(url, timeout=1)
    except Exception:
        pass


def hook_post_tool():
    """PostToolUse hook: send ERROR on failure, THINKING on success."""
    try:
        chunk = sys.stdin.buffer.read(4096)
        if b'"is_error": true' in chunk or b'"is_error":true' in chunk:
            send("ERROR")
        else:
            send("THINKING")
    except Exception:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "hook-post":
        hook_post_tool()
    elif cmd.upper() in ("THINKING", "EXECUTING", "DONE", "ERROR", "IDLE"):
        send(cmd.upper())

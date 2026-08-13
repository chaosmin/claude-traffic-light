#!/usr/bin/env python3
"""
Claude Code traffic light controller — WiFi edition.
Usage:
  claude_light.py THINKING   - chase animation (Claude reasoning)
  claude_light.py EXECUTING  - yellow solid (tool running)
  claude_light.py DONE       - green (auto-transitions to IDLE after 60s on ESP32)
  claude_light.py ERROR      - red solid
  claude_light.py IDLE       - all off
  claude_light.py WAITING    - onboard NeoPixel blue (needs your input), overlays main state
  claude_light.py hook-post  - read PostToolUse JSON from stdin, send ERROR or THINKING

ESP32 hostname: set CLAUDE_LIGHT_HOST env var, default: esp32-traffic-light.local
"""

import socket
import sys
import os
import time
import urllib.request

# mDNS hostname or IP of the ESP32
WIFI_HOST = os.environ.get("CLAUDE_LIGHT_HOST", "esp32-traffic-light.local")

# Cache the resolved IP so we don't pay mDNS resolution cost (unbounded by
# urlopen's timeout — getaddrinfo runs before the socket timeout applies) on
# every single call. Re-resolve if the cache is stale or the cached IP fails.
IP_CACHE_FILE = "/tmp/claude_light_ip_cache"
IP_CACHE_TTL = 3600


def _resolve_host():
    if not WIFI_HOST.endswith(".local"):
        return WIFI_HOST
    try:
        mtime = os.path.getmtime(IP_CACHE_FILE)
        if time.time() - mtime < IP_CACHE_TTL:
            with open(IP_CACHE_FILE) as f:
                return f.read().strip()
    except OSError:
        pass
    ip = socket.gethostbyname(WIFI_HOST)
    try:
        with open(IP_CACHE_FILE, "w") as f:
            f.write(ip)
    except OSError:
        pass
    return ip


def send(state: str):
    try:
        host = _resolve_host()
        url = f"http://{host}/cmd?state={state}"
        urllib.request.urlopen(url, timeout=1)
    except Exception:
        try:
            os.remove(IP_CACHE_FILE)
        except OSError:
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
    elif cmd.upper() in ("THINKING", "EXECUTING", "DONE", "ERROR", "IDLE", "WAITING"):
        send(cmd.upper())

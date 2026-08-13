# claude-traffic-light

Physical traffic light for Claude Code — shows AI state in real time via ESP32-S3 + WiFi.

## States

| State | LED | Hook | Trigger |
|-------|-----|------|---------|
| THINKING | Chase animation (R→Y→G) | UserPromptSubmit | User sent a message, Claude starts working |
| EXECUTING | Yellow solid | PreToolUse | Tool call running |
| DONE | Green solid (60s, then auto IDLE) | Stop | Turn complete |
| ERROR | Red solid | PostToolUse (on failure) | Tool call failed |
| WAITING | Onboard NeoPixel solid blue (overlay — main LEDs untouched) | Notification | Claude needs your input (permission prompt / idle nudge) |
| IDLE | All off | — | No active turn |

`PostToolUse` also fires on success and resends `THINKING` (Claude resumes reasoning over the tool result).

## Hardware

- **Board**: YD-ESP32-S3 (N16R8)
- **LEDs**: Red / Yellow / Green on GPIO 4 / 5 / 6
- **Onboard RGB**: WS2812 on GPIO 48 (blink confirmation)

## Setup

### Firmware

1. Install Arduino IDE, add ESP32 board support
2. Install libraries: `Adafruit NeoPixel`, `WiFiManager`
3. Flash `firmware/traffic_light/traffic_light.ino`
4. On first boot, connect to `TrafficLight-Setup` hotspot and configure WiFi
5. Device reachable at `http://esp32-traffic-light.local`

> Hold BOOT button on power-up to reset WiFi credentials.

### Claude Code hooks

Add to `~/.claude/settings.json` (replace `/path/to` with the absolute path to this repo):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [{"type": "command", "command": "python3 /path/to/scripts/claude_light.py THINKING"}]
      }
    ],
    "PreToolUse": [
      {
        "matcher": ".*",
        "hooks": [{"type": "command", "command": "python3 /path/to/scripts/claude_light.py EXECUTING"}]
      }
    ],
    "PostToolUse": [
      {
        "matcher": ".*",
        "hooks": [{"type": "command", "command": "python3 /path/to/scripts/claude_light.py hook-post"}]
      }
    ],
    "Notification": [
      {
        "hooks": [{"type": "command", "command": "python3 /path/to/scripts/claude_light.py WAITING"}]
      }
    ],
    "Stop": [
      {
        "hooks": [{"type": "command", "command": "python3 /path/to/scripts/claude_light.py DONE"}]
      }
    ]
  }
}
```

- `UserPromptSubmit` fires when the user submits a message → sends `THINKING` (chase animation).
- `PreToolUse` fires before every tool call → sends `EXECUTING` (yellow solid).
- `PostToolUse` fires after every tool call → reads the tool result from stdin, sends `ERROR` if it failed, otherwise `THINKING` (resumes reasoning).
- `Notification` fires when Claude needs your input (permission prompt, idle nudge) → sends `WAITING` (onboard NeoPixel blue overlay, main LEDs untouched).
- `Stop` fires when Claude finishes responding → sends `DONE` (green, auto-reverts to `IDLE` after 60s).

### Environment

```bash
# Optional: override mDNS hostname or use IP
export CLAUDE_LIGHT_HOST=esp32-traffic-light.local
```

## API

```
GET /cmd?state=THINKING
GET /cmd?state=EXECUTING
GET /cmd?state=DONE
GET /cmd?state=ERROR
GET /cmd?state=IDLE
GET /cmd?state=WAITING
GET /status
```

## Ideas for later (needs new hardware)

Not implemented yet — notes for when parts arrive.

1. **OLED (SSD1306, I2C)** — recommended first pick. Complements the LEDs instead of duplicating them: show current tool name, turn duration, connection status, error count. I2C is free (no pin conflict with 4/5/6/48).
2. **Passive buzzer** — beep on `WAITING` (permission prompt / idle nudge) so it's audible from another room, not just visible.
3. **WS2812 LED strip** (8–30px) instead of the single onboard pixel — smoother chase/breathing animation, could show a progress-bar-style effect during THINKING.
4. **Physical button → approve action** — a button wired to a new HTTP endpoint that Claude Code or a companion script polls, to physically approve a pending permission prompt during `WAITING`.
5. **BLE instead of WiFi** — drop the LAN/mDNS dependency for a portable battery setup. Biggest rework: replaces the whole WebServer/HTTP layer.

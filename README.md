# claude-traffic-light

Physical traffic light for Claude Code — shows AI state in real time via ESP32-S3 + WiFi.

## States

| State | LED | Trigger |
|-------|-----|---------|
| THINKING | Chase animation (R→Y→G) | Claude reasoning |
| EXECUTING | Yellow solid | Tool call running |
| DONE | Green solid (60s) | Task complete |
| ERROR | Red solid | Tool error |
| IDLE | All off | Waiting |

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

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "python3 /path/to/scripts/claude_light.py EXECUTING"}]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "python3 /path/to/scripts/claude_light.py hook-post"}]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "python3 /path/to/scripts/claude_light.py DONE"}]
      }
    ]
  }
}
```

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
GET /status
```

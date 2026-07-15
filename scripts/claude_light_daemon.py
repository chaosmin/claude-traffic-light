#!/usr/bin/env python3
"""
Traffic light daemon — keeps serial port open to avoid CH340 reset-on-connect.
Listens on a Unix socket for commands from claude_light.py.

Start once (e.g. at login):
  python3 claude_light_daemon.py &

LaunchAgent plist: see README or run with launchctl.
"""

import socket
import os
import sys
import glob
import time
import threading
import queue
import signal

SOCKET_PATH = "/tmp/claude_light.sock"
BAUD_RATE   = 115200
SERIAL_PORT = os.environ.get("CLAUDE_LIGHT_PORT", "")

VALID_CMDS = {"THINKING", "EXECUTING", "DONE", "ERROR", "IDLE"}


def find_port():
    if SERIAL_PORT and os.path.exists(SERIAL_PORT):
        return SERIAL_PORT
    for pattern in ("/dev/cu.usbserial*", "/dev/cu.usbmodem*", "/dev/ttyUSB*", "/dev/ttyACM*"):
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def serial_worker(cmd_queue):
    """Keeps serial port open; drains command queue. Reconnects on error."""
    import serial

    while True:
        port = find_port()
        if not port:
            time.sleep(2)
            continue

        print(f"[daemon] opening {port}", flush=True)
        try:
            with serial.Serial(port, BAUD_RATE, timeout=1, dsrdtr=False, rtscts=False) as ser:
                ser.dtr = False
                ser.rts = False
                time.sleep(1.5)  # one-time wait for board boot after initial open
                print("[daemon] serial ready", flush=True)

                while True:
                    cmd = cmd_queue.get()
                    if cmd is None:  # shutdown
                        return
                    try:
                        ser.write(f"{cmd}\n".encode())
                        ser.flush()
                        print(f"[daemon] sent {cmd}", flush=True)
                    except Exception as e:
                        print(f"[daemon] write error: {e}", flush=True)
                        cmd_queue.put(cmd)  # requeue for retry after reconnect
                        break

        except Exception as e:
            print(f"[daemon] serial error: {e}", flush=True)
            time.sleep(2)


def run():
    cmd_queue = queue.Queue()

    t = threading.Thread(target=serial_worker, args=(cmd_queue,), daemon=True)
    t.start()

    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o600)
    server.listen(5)
    print(f"[daemon] listening on {SOCKET_PATH}", flush=True)

    def shutdown(sig, frame):
        cmd_queue.put(None)
        server.close()
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while True:
        try:
            conn, _ = server.accept()
            with conn:
                data = conn.recv(64).decode().strip().upper()
                if data in VALID_CMDS:
                    cmd_queue.put(data)
                    conn.send(b"OK\n")
                else:
                    conn.send(b"ERR\n")
        except Exception:
            break


if __name__ == "__main__":
    run()

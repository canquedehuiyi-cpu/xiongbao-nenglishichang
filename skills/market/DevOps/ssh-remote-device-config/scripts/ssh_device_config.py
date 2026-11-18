"""
SSH into a single H3C/Comware network device and apply configuration.
Supports legacy SSH algorithms (ssh-rsa/ssh-dss) via paramiko 2.x.

Usage:
  python ssh_device_config.py --ip <IP> --user <USER> --config <CONFIG_FILE> [--passwords pw1,pw2,...] [--port 22]

Output: JSON result to stdout.
"""
import paramiko
import time
import argparse
import json
import sys
import re
import os

def read_config(filepath):
    lines = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if line.startswith("==="):
                continue
            lines.append(line)
    return lines

def apply_config(ip, port, username, password, config_lines):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, port=port, username=username, password=password,
                       timeout=15, look_for_keys=False, allow_agent=False)
    except Exception as e:
        return {"success": False, "error": f"Connection failed: {e}"}

    shell = client.invoke_shell(width=200, height=50)
    time.sleep(2)
    while shell.recv_ready():
        shell.recv(65536)

    def send_cmd(cmd, wait=0.8):
        shell.send(cmd + "\n")
        time.sleep(wait)
        out = ""
        while shell.recv_ready():
            out += shell.recv(65536).decode("utf-8", errors="ignore")
        return out

    send_cmd("system-view", wait=2)

    errors = []
    for line in config_lines:
        stripped = line.strip()
        if stripped == "" or stripped == "#":
            continue
        out = send_cmd(stripped, wait=0.5)
        if "Error" in out or "error" in out.lower():
            errors.append({"command": stripped, "response": out.strip()})

    out = send_cmd("return", wait=1)
    out = send_cmd("save force", wait=3)
    save_ok = "saved to device" in out.lower() or "successfully" in out.lower()

    shell.close()
    client.close()

    return {
        "success": True,
        "save_success": save_ok,
        "save_output": out.strip()[:300],
        "errors": errors
    }

def main():
    parser = argparse.ArgumentParser(description="SSH device config applier")
    parser.add_argument("--ip", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--config", required=True, help="Path to config txt file")
    parser.add_argument("--passwords", required=True, help="Comma-separated password candidates")
    parser.add_argument("--port", type=int, default=22)
    args = parser.parse_args()

    passwords = [p.strip() for p in args.passwords.split(",")]
    config_lines = read_config(args.config)

    for pw in passwords:
        result = apply_config(args.ip, args.port, args.user, pw, config_lines)
        if result.get("success"):
            result["password_used"] = pw
            print(json.dumps(result, ensure_ascii=False, indent=2))
            sys.exit(0)

    print(json.dumps({"success": False, "error": "All passwords failed"}, ensure_ascii=False, indent=2))
    sys.exit(1)

if __name__ == "__main__":
    main()

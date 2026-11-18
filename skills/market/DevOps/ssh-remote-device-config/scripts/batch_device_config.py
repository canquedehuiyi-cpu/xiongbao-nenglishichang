"""
Batch SSH config: read IPs from Excel, match to config txt files, apply to devices.

Usage:
  python batch_device_config.py --excel <EXCEL_FILE> --config-dir <DIR> --user <USER> \
    [--passwords pw1,pw2,...] [--col 26] [--start-row 159] [--end-row 382] \
    [--log result.json] [--name-col 1] [--preflight]

Features:
  - Reads IPs from specified Excel column
  - Skips rows marked as device offline (设备不在线/离线)
  - Matches IP to config file by filename pattern *(IP).txt
  - Tries multiple passwords in order
  - Saves progress to log file for resume capability
  - Preflight mode: verify IP-to-config matching without connecting
  - Outputs summary to stdout
"""
import paramiko
import time
import os
import re
import glob
import json
import sys
import argparse


def read_config(filepath):
    lines = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if line.startswith("==="):
                continue
            lines.append(line)
    return lines


def find_config_file(ip, config_dir):
    pattern = os.path.join(config_dir, f"*({ip}).txt")
    matches = glob.glob(pattern)
    if matches:
        fname = os.path.basename(matches[0])
        ip_match = re.search(r'\(([\d.]+)\)', fname)
        if ip_match and ip_match.group(1) == ip:
            return matches[0]
    return None


def apply_config(ip, port, username, password, config_lines):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(ip, port=port, username=username, password=password,
                       timeout=15, look_for_keys=False, allow_agent=False)
    except Exception as e:
        return None, str(e)

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
            errors.append(f"{stripped} -> {out.strip()}")

    out = send_cmd("return", wait=1)
    out = send_cmd("save force", wait=3)
    save_ok = "saved to device" in out.lower() or "successfully" in out.lower()

    shell.close()
    client.close()

    return password, {
        "save_success": save_ok,
        "save_output": out.strip()[:300],
        "errors": errors
    }


def scan_tasks(ws, args, config_dir):
    tasks = []
    skipped = {"empty": 0, "offline": 0, "invalid_ip": 0, "no_config": 0}

    for r in range(args.start_row, args.end_row + 1):
        ip = ws.cell(row=r, column=args.col).value
        name = ws.cell(row=r, column=args.name_col).value or ""
        if not ip:
            skipped["empty"] += 1
            continue
        ip = str(ip).strip()
        if "不在线" in ip or "离线" in ip:
            print(f"[SKIP] Row {r}: {name} - offline")
            sys.stdout.flush()
            skipped["offline"] += 1
            continue
        if not re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
            print(f"[SKIP] Row {r}: {name} - invalid: {ip}")
            sys.stdout.flush()
            skipped["invalid_ip"] += 1
            continue
        cfg = find_config_file(ip, config_dir)
        if not cfg:
            print(f"[SKIP] Row {r}: {ip} ({name}) - no config file")
            sys.stdout.flush()
            skipped["no_config"] += 1
            continue
        tasks.append((r, ip, str(name), cfg))

    return tasks, skipped


def preflight(ws, args, config_dir):
    print(f"{'='*60}")
    print(f"PREFLIGHT CHECK")
    print(f"{'='*60}")
    print(f"Excel: {args.excel}")
    print(f"Config dir: {config_dir}")
    print(f"Row range: {args.start_row} - {args.end_row}")
    print(f"IP column: {args.col}")
    print()

    tasks, skipped = scan_tasks(ws, args, config_dir)

    total = args.end_row - args.start_row + 1
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total rows scanned: {total}")
    print(f"Matched (ready to config): {len(tasks)}")
    print(f"Skipped:")
    print(f"  Empty IP: {skipped['empty']}")
    print(f"  Offline: {skipped['offline']}")
    print(f"  Invalid IP format: {skipped['invalid_ip']}")
    print(f"  No config file: {skipped['no_config']}")

    if tasks:
        print(f"\nMatched devices:")
        for row, ip, name, cfg in tasks:
            print(f"  Row {row}: {name} ({ip}) -> {os.path.basename(cfg)}")

    return len(tasks)


def main():
    parser = argparse.ArgumentParser(description="Batch SSH device config")
    parser.add_argument("--excel", required=True)
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--passwords", required=True, help="Comma-separated password candidates")
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--col", type=int, default=26, help="Column number for IP (default 26=Z)")
    parser.add_argument("--name-col", type=int, default=1, help="Column number for device name (default 1=A)")
    parser.add_argument("--start-row", type=int, required=True)
    parser.add_argument("--end-row", type=int, required=True)
    parser.add_argument("--log", default="batch_result.json")
    parser.add_argument("--preflight", action="store_true", help="Only check IP-to-config matching, don't connect")
    args = parser.parse_args()

    import openpyxl
    wb = openpyxl.load_workbook(args.excel, data_only=True)
    ws = wb.active
    passwords = [p.strip() for p in args.passwords.split(",")]

    config_dir = args.config_dir
    if not os.path.isdir(config_dir):
        print(f"ERROR: Config directory not found: {config_dir}")
        sys.exit(1)

    if args.preflight:
        matched = preflight(ws, args, config_dir)
        sys.exit(0 if matched > 0 else 1)

    tasks, skipped = scan_tasks(ws, args, config_dir)

    results = []
    done_ips = set()
    if os.path.exists(args.log):
        try:
            with open(args.log, "r", encoding="utf-8") as f:
                results = json.load(f)
            done_ips = {r["ip"] for r in results if r.get("status") == "OK"}
            print(f"[RESUME] {len(done_ips)} already done\n")
            sys.stdout.flush()
        except Exception:
            pass

    remaining = len(tasks) - len(done_ips)
    print(f"{'='*60}")
    print(f"Total: {len(tasks)}, Remaining: {remaining}")
    print(f"{'='*60}\n")
    sys.stdout.flush()

    for idx, (row, ip, name, cfg) in enumerate(tasks, 1):
        if ip in done_ips:
            continue
        print(f"[{idx}/{len(tasks)}] Row {row}: {name} ({ip})")
        sys.stdout.flush()

        config_lines = read_config(cfg)
        success = False

        for pw in passwords:
            ret_pw, result = apply_config(ip, args.port, args.user, pw, config_lines)
            if not isinstance(result, dict):
                print(f"  PW {pw[:4]}**** failed: {result}")
                sys.stdout.flush()
                continue
            if result["errors"]:
                print(f"  Config errors: {result['errors']}")
            print(f"  Save: {'OK' if result['save_success'] else 'FAILED'} | PW: {pw[:4]}****")
            sys.stdout.flush()
            results.append({
                "row": row, "ip": ip, "name": name,
                "config_file": os.path.basename(cfg),
                "status": "OK", "password": pw, "detail": result
            })
            success = True
            break

        if not success:
            print(f"  FAILED: all passwords rejected")
            sys.stdout.flush()
            results.append({
                "row": row, "ip": ip, "name": name,
                "config_file": os.path.basename(cfg),
                "status": "FAILED", "password": None
            })

        with open(args.log, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for r in results if r.get("status") == "OK")
    fail = sum(1 for r in results if r.get("status") != "OK")
    print(f"\n{'='*60}")
    print(f"DONE: {ok} OK, {fail} FAILED, {len(results)} total")
    failed = [r for r in results if r.get("status") != "OK"]
    if failed:
        print("Failed:")
        for r in failed:
            reason = r.get("detail", "")
            if isinstance(reason, dict):
                reason = "config errors" if reason.get("errors") else "save failed"
            print(f"  Row {r['row']}: {r['ip']} ({r['name']}) - {reason}")
    print(f"Log: {args.log}")


if __name__ == "__main__":
    main()

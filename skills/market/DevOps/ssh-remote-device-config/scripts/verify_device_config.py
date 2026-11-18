"""
Verify device configuration by SSH into devices and running check commands.

Usage:
  python verify_device_config.py --log result.json --user admin \
    [--command "display ipv6 interface brief"] \
    [--check-keyword "GE" "Vlan" "::"] \
    [--verify-log verify_result.json] \
    [--export-csv ip_password_mapping.csv]

Reads device IP/password from a batch result log, SSH into each device,
runs the specified command, and checks if the output contains expected keywords.
"""
import paramiko
import time
import json
import sys
import csv
import os
import argparse


def verify_device(ip, port, username, password, command):
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

    try:
        out = send_cmd(command, wait=3)
    except Exception as e:
        shell.close()
        client.close()
        return None, f"Socket error: {e}"

    shell.close()
    client.close()
    return password, out


def main():
    parser = argparse.ArgumentParser(description="Verify device configuration")
    parser.add_argument("--log", required=True, help="Batch result log file (JSON)")
    parser.add_argument("--user", required=True, help="SSH username")
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--command", default="display ipv6 interface brief",
                        help="Command to run on each device")
    parser.add_argument("--check-keyword", nargs="+", default=["GE", "Vlan", "::"],
                        help="Keywords to check in output (any match = pass)")
    parser.add_argument("--verify-log", default="verify_result.json",
                        help="Output verification log file")
    parser.add_argument("--export-csv", default=None,
                        help="Export IP-password mapping to CSV")
    parser.add_argument("--status-only", action="store_true",
                        help="Only check SSH connectivity, don't run commands")
    args = parser.parse_args()

    with open(args.log, "r", encoding="utf-8") as f:
        results = json.load(f)

    ok_devices = [r for r in results if r.get("status") == "OK"]
    failed_devices = [r for r in results if r.get("status") != "OK"]

    if args.export_csv:
        with open(args.export_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Row", "Name", "IP", "Password", "Config File"])
            for r in ok_devices:
                pw = r.get("password") or r.get("password_tried", "")
                writer.writerow([r["row"], r["name"], r["ip"], pw, r.get("config_file", "")])
        print(f"[EXPORT] IP-password mapping saved to {args.export_csv} ({len(ok_devices)} entries)")
        sys.stdout.flush()

    verify_results = []
    done_ips = set()
    if os.path.exists(args.verify_log):
        try:
            with open(args.verify_log, "r", encoding="utf-8") as f:
                verify_results = json.load(f)
            done_ips = {r["ip"] for r in verify_results if r.get("verify_status") == "OK"}
            print(f"[RESUME] {len(done_ips)} already verified\n")
            sys.stdout.flush()
        except Exception:
            pass

    print(f"{'='*60}")
    print(f"VERIFICATION")
    print(f"Command: {args.command}")
    print(f"Keywords: {args.check_keyword}")
    print(f"Total OK devices: {len(ok_devices)}, Remaining: {len(ok_devices) - len(done_ips)}")
    print(f"{'='*60}\n")
    sys.stdout.flush()

    for idx, dev in enumerate(ok_devices, 1):
        ip = dev["ip"]
        if ip in done_ips:
            continue

        name = dev["name"]
        pw = dev.get("password") or dev.get("password_tried", "")
        print(f"[{idx}/{len(ok_devices)}] {name} ({ip})")
        sys.stdout.flush()

        ret_pw, output = verify_device(ip, args.port, args.user, pw, args.command)
        if ret_pw is None:
            print(f"  VERIFY FAILED: {output}")
            sys.stdout.flush()
            verify_results.append({
                "row": dev["row"], "ip": ip, "name": name,
                "verify_status": "FAILED", "error": output, "output": ""
            })
        else:
            if args.status_only:
                check_passed = True
                print(f"  SSH OK")
            else:
                check_passed = any(kw in output for kw in args.check_keyword)
                print(f"  VERIFY {'OK' if check_passed else 'WARN'} | Check passed: {check_passed}")
                if not check_passed:
                    print(f"  WARNING: None of {args.check_keyword} found in output")
            sys.stdout.flush()
            verify_results.append({
                "row": dev["row"], "ip": ip, "name": name,
                "verify_status": "OK", "check_passed": check_passed,
                "output": output.strip()[:2000]
            })

        with open(args.verify_log, "w", encoding="utf-8") as f:
            json.dump(verify_results, f, ensure_ascii=False, indent=2)

    v_ok = sum(1 for r in verify_results if r.get("verify_status") == "OK")
    v_fail = sum(1 for r in verify_results if r.get("verify_status") != "OK")
    v_pass = sum(1 for r in verify_results if r.get("check_passed") is True)
    v_warn = sum(1 for r in verify_results if r.get("verify_status") == "OK" and r.get("check_passed") is False)

    print(f"\n{'='*60}")
    print(f"VERIFICATION DONE")
    print(f"  Total verified: {len(verify_results)}")
    print(f"  SSH OK: {v_ok}, SSH Failed: {v_fail}")
    if not args.status_only:
        print(f"  Check passed: {v_pass}, Check warning: {v_warn}")
    print(f"{'='*60}")

    if v_warn > 0:
        print(f"\nDevices with check warnings:")
        for r in verify_results:
            if r.get("verify_status") == "OK" and r.get("check_passed") is False:
                print(f"  Row {r['row']}: {r['ip']} ({r['name']})")

    if v_fail > 0:
        print(f"\nDevices SSH failed:")
        for r in verify_results:
            if r.get("verify_status") != "OK":
                print(f"  Row {r['row']}: {r['ip']} ({r['name']}) - {r.get('error', '')}")

    if failed_devices:
        print(f"\nFailed devices from config batch ({len(failed_devices)}):")
        for r in failed_devices:
            print(f"  Row {r['row']}: {r['ip']} ({r['name']})")

    print(f"\nFiles:")
    print(f"  Verification log: {args.verify_log}")
    if args.export_csv:
        print(f"  IP-Password mapping: {args.export_csv}")


if __name__ == "__main__":
    main()

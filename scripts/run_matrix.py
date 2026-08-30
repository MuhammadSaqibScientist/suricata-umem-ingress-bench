#!/usr/bin/env python3
"""
run_matrix.py - Automated Ingress Pipeline Benchmark Suite
Project: Optimizing the Ingress Pipeline (AF_PACKET vs AF_XDP Suricata Performance)
"""

import os
import sys
import time
import shutil
import subprocess
import itertools
from pathlib import Path

# --- Configuration & Matrix Parameters ---
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "configs"
DATA_DIR = BASE_DIR / "bench_data"
NETNS_SCRIPT = BASE_DIR / "scripts" / "setup_netns.sh"

# CPU Pinning allocations (taskset masks/ranges)
SENDER_CPUS = "0-1"      # Cores pinned for traffic injection
SURICATA_CPUS = "2-3"    # Cores pinned for Suricata worker threads

# Benchmark parameters
OFFERED_LOADS = [100000, 250000, 500000, 1000000]  # pps
BATCH_SIZES = [16, 32, 64, 128]
RING_SIZES = [512, 1024, 2048, 4096]
DURATION = 10  # Seconds per iteration test run

def run_cmd(cmd, check=True, env=None):
    """Executes system command via subprocess."""
    res = subprocess.run(cmd, shell=True, env=env, text=True, capture_output=True)
    if check and res.returncode != 0:
        print(f"[!] Command failed: {cmd}\n[!] Error: {res.stderr}")
        sys.exit(res.returncode)
    return res.stdout

def setup_environment(action="up"):
    """Tears down or brings up network namespaces."""
    run_cmd(f"sudo {NETNS_SCRIPT} {action}")

def execute_suricata_iteration(mode, mode_flag, config_file, load, batch, ring, env):
    """Executes an isolated Suricata run with clean log tracking."""
    pid_file = f"/tmp/suricata_bench_{int(time.time())}.pid"
    log_dir = Path(f"/tmp/suricata_logs_{int(time.time())}")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    SURICATA_BIN = "/usr/bin/suricata"
    out_dir = DATA_DIR / mode
    out_dir.mkdir(parents=True, exist_ok=True)
    
    run_id = f"load_{load}_batch_{batch}_ring_{ring}"
    dest_log = out_dir / f"stats_{run_id}.log"

    # Define traffic generator command with packet limit matching load
    pktgen_cmd = (
        f"sudo taskset -c {SENDER_CPUS} ip netns exec sender "
        f"ping -f -c {load} 192.168.10.2 > /dev/null 2>&1 || true"
    )

    # Build execution command using isolated log directories (-l)
    suricata_cmd = [
        "sudo", "taskset", "-c", SURICATA_CPUS,
        "ip", "netns", "exec", "receiver",
        SURICATA_BIN,
        "-c", str(CONFIG_DIR / config_file),
        f"--{mode_flag}=veth_rx",
        "-l", str(log_dir),
        "--pidfile", pid_file,
        "-D"
    ]

    try:
        # Wipe old default log files if present
        run_cmd("sudo rm -f /var/log/suricata/stats.log ./stats.log", check=False)

        # Launch Suricata in Daemon mode
        run_cmd(" ".join(suricata_cmd), env=env)
        time.sleep(2)  # Wait for worker threads initialization

        # Inject traffic
        try:
            subprocess.run(
                pktgen_cmd,
                shell=True,
                timeout=DURATION + 2,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except subprocess.TimeoutExpired:
            pass

    finally:
        # Stop Suricata cleanly to force stats flush
        if os.path.exists(pid_file):
            try:
                with open(pid_file, "r") as f:
                    pid = f.read().strip()
                run_cmd(f"sudo kill -15 {pid}", check=False)
                time.sleep(1)
            except Exception:
                pass
        
        run_cmd("sudo pkill -9 suricata", check=False)

        # Copy isolated stats.log to bench_data
        isolated_stats = log_dir / "stats.log"
        if isolated_stats.exists():
            shutil.copy(isolated_stats, dest_log)

        # Cleanup isolated temporary logs
        shutil.rmtree(log_dir, ignore_errors=True)
        run_cmd(f"sudo rm -f {pid_file}", check=False)
        time.sleep(1)

def benchmark_af_packet():
    """Sweeps AF_PACKET parameters completely and saves all metrics."""
    print("\n===========================================")
    print(" [1/2] Executing AF_PACKET Benchmark Sweep ")
    print("===========================================")
    
    for load, batch, ring in itertools.product(OFFERED_LOADS, BATCH_SIZES, RING_SIZES):
        print(f"[+] Running AF_PACKET -> Load: {load}pps | Batch: {batch} | Ring: {ring}")

        env = os.environ.copy()
        env["AF_PACKET_RING_SIZE"] = str(ring)
        env["AF_PACKET_MAX_PENDING"] = str(ring * 4)
        env["SURICATA_IFACE"] = "veth_rx"
        env["SURICATA_THREADS"] = "2"

        execute_suricata_iteration("af_packet", "af-packet", "af_packet.yaml", load, batch, ring, env)

def benchmark_af_xdp():
    """Sweeps AF_XDP parameters completely and saves all metrics."""
    print("\n========================================")
    print(" [2/2] Executing AF_XDP Benchmark Sweep ")
    print("========================================")
    
    for load, batch, ring in itertools.product(OFFERED_LOADS, BATCH_SIZES, RING_SIZES):
        print(f"[+] Running AF_XDP -> Load: {load}pps | Batch: {batch} | Ring: {ring}")

        env = os.environ.copy()
        env["AF_XDP_BATCH_SIZE"] = str(batch)
        env["AF_XDP_FILL_RING"] = str(ring)
        env["AF_XDP_COMPLETION_RING"] = str(ring)
        env["AF_XDP_RX_RING"] = str(ring)
        env["AF_XDP_TX_RING"] = str(ring)
        env["AF_XDP_MODE"] = "skb"
        env["SURICATA_IFACE"] = "veth_rx"
        env["SURICATA_THREADS"] = "2"

        execute_suricata_iteration("af_xdp", "af-xdp", "af_xdp.yaml", load, batch, ring, env)

def main():
    if os.geteuid() != 0:
        print("[!] Error: This script must be executed with root privileges (sudo).")
        sys.exit(1)

    print("[+] Initializing automated benchmark suite...")
    setup_environment("up")

    try:
        benchmark_af_packet() 
        benchmark_af_xdp()
        print("\n[✔] Full benchmark sweep completed successfully!")
        print(f"[✔] Metrics stored in: {DATA_DIR}")
    finally:
        setup_environment("down")

if __name__ == "__main__":
    main()

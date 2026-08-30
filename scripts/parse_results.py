#!/usr/bin/env python3
"""
parse_results.py - Parse and Compare Suricata Benchmark Metrics
"""

import os
import re
import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "bench_data"
RESULTS_FILE = BASE_DIR / "benchmark_summary.json"
CSV_FILE = BASE_DIR / "benchmark_summary.csv"

def parse_stats_log(filepath):
    """Extracts packet capture and drop counters from a Suricata stats.log file."""
    metrics = {
        "kernel_packets": 0,
        "kernel_drops": 0,
        "decoder_pkts": 0,
    }
    
    if not os.path.exists(filepath):
        return metrics

    with open(filepath, "r") as f:
        for line in f:
            if "capture.kernel_packets" in line:
                match = re.search(r"\|\s+(\d+)", line)
                if match:
                    metrics["kernel_packets"] = int(match.group(1))
            elif "capture.kernel_drops" in line:
                match = re.search(r"\|\s+(\d+)", line)
                if match:
                    metrics["kernel_drops"] = int(match.group(1))
            elif "decoder.pkts" in line:
                match = re.search(r"\|\s+(\d+)", line)
                if match:
                    metrics["decoder_pkts"] = int(match.group(1))

    return metrics

def main():
    results = []

    for mode in ["af_packet", "af_xdp"]:
        mode_dir = DATA_DIR / mode
        if not mode_dir.exists():
            continue

        for log_file in mode_dir.glob("stats_load_*.log"):
            # Extract parameters from filename: stats_load_100000_batch_16_ring_512.log
            filename = log_file.stem
            parts = filename.split("_")
            
            try:
                load = int(parts[2])
                batch = int(parts[4])
                ring = int(parts[6])
            except (IndexError, ValueError):
                continue

            metrics = parse_stats_log(log_file)
            
            pkts = metrics["kernel_packets"] or metrics["decoder_pkts"]
            drops = metrics["kernel_drops"]
            drop_pct = (drops / pkts * 100) if pkts > 0 else 0.0

            results.append({
                "mode": mode,
                "offered_load_pps": load,
                "batch_size": batch,
                "ring_size": ring,
                "processed_pkts": pkts,
                "dropped_pkts": drops,
                "drop_rate_pct": round(drop_pct, 2)
            })

    if not results:
        print("[!] No benchmark data logs found to parse.")
        return

    df = pd.DataFrame(results)
    
    # Save structured summary
    df.to_csv(CSV_FILE, index=False)
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print("\n=========================================================================")
    print("                    BENCHMARK COMPARISON SUMMARY                         ")
    print("=========================================================================\n")
    print(df.to_string(index=False))
    print(f"\n[✔] Structured data saved to:\n - {CSV_FILE}\n - {RESULTS_FILE}")

if __name__ == "__main__":
    main()

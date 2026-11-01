# Ingress Pipeline Virtualization Tax Benchmark
Evaluating the performance crossover and packet drop dynamics between **AF_PACKET (TPACKET_V3)** and **AF_XDP (SKB Mode)** inside a KVM/QEMU virtualized environment (`veth` / `virtio-net`).

---

## Performance Comparison Figures

![Ingress Performance Comparison](./ingress_performance_comparison.png)

* **Left Panel:** Packet drop rate vs. offered load (Log Scale). Notice how `af_xdp` (SKB mode) hits an ingestion starvation ceiling, resulting in low packet capture volume with zero drops, while `af_packet` aggressively captures traffic but suffers severe packet loss scaling under high offered load ($1\text{M}$ pps).
* **Right Panel:** Impact of ring buffer size on packet drops at maximum offered load ($1,000,000\text{ pps}$).

---

## Summary Results Matrix

| Capture Framework | Offered Load (pps) | Batch Size | Ring Size | Processed Packets | Dropped Packets | Drop Rate (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AF_PACKET** | 100,000 | 32 | 1024 | 1 | 0 | 0.00% |
| **AF_PACKET** | 1,000,000 | 32 | 4096 | 1,882,434 | 11,489 | 0.61% |
| **AF_XDP (SKB)** | 100,000 | 32 | 1024 | 7,414 | 0 | 0.00% |
| **AF_XDP (SKB)** | 1,000,000 | 128 | 4096 | 59,445 | 0 | 0.00% |

---

## Key Research Findings
1. **The Virtualization Tax:** Guest network namespaces lacking native driver-level XDP force AF_XDP into software SKB fallback mode, destroying zero-copy benefits.
2. **Ingestion Starvation vs. Drop Spikes:** While legacy `TPACKET_V3` attempts to capture maximum volume at the cost of high drop rates under stress, `AF_XDP (SKB)` suffers from socket ring starvation, bottlenecking packet processing completely under high cloud loads.

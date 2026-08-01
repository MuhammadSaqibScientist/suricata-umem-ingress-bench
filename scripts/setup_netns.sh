#!/usr/bin/env bash
#
# setup_netns.sh - Isolate testing environment using Linux Network Namespaces
# Project: Optimizing the Ingress Pipeline (AF_PACKET vs AF_XDP Suricata Performance)

set -euo pipefail

SENDER_NS="sender"
RECEIVER_NS="receiver"
VETH_TX="veth_tx"
VETH_RX="veth_rx"
IP_TX="192.168.10.1/24"
IP_RX="192.168.10.2/24"

usage() {
    echo "Usage: sudo $0 {up|down|status}"
    exit 1
}

if [[ $EUID -ne 0 ]]; then
   echo "[!] Error: This script must be run as root (sudo)." 
   exit 1
fi

MODE="${1:-}"

case "$MODE" in
    up)
        echo "[+] Cleaning any old namespaces/interfaces..."
        ip netns del "$SENDER_NS" 2>/dev/null || true
        ip netns del "$RECEIVER_NS" 2>/dev/null || true

        echo "[+] Creating namespaces: '$SENDER_NS' and '$RECEIVER_NS'..."
        ip netns add "$SENDER_NS"
        ip netns add "$RECEIVER_NS"

        echo "[+] Creating veth pair: $VETH_TX <---> $VETH_RX..."
        ip link add "$VETH_TX" type veth peer name "$VETH_RX"

        echo "[+] Moving $VETH_TX to '$SENDER_NS' and $VETH_RX to '$RECEIVER_NS'..."
        ip link set "$VETH_TX" netns "$SENDER_NS"
        ip link set "$VETH_RX" netns "$RECEIVER_NS"

        echo "[+] Configuring network interfaces..."
        # Sender setup
        ip netns exec "$SENDER_NS" ip link set lo up
        ip netns exec "$SENDER_NS" ip addr add "$IP_TX" dev "$VETH_TX"
        ip netns exec "$SENDER_NS" ip link set "$VETH_TX" up

        # Receiver setup
        ip netns exec "$RECEIVER_NS" ip link set lo up
        ip netns exec "$RECEIVER_NS" ip addr add "$IP_RX" dev "$VETH_RX"
        ip netns exec "$RECEIVER_NS" ip link set "$VETH_RX" up

        # Increase ring buffers and queues on veth interfaces for heavy benchmark loads
        ip netns exec "$SENDER_NS" ip link set dev "$VETH_TX" txqueuelen 10000
        ip netns exec "$RECEIVER_NS" ip link set dev "$VETH_RX" txqueuelen 10000

        echo "[✔] Isolated Network Testbed Ready!"
        echo "    - Sender NS:   $SENDER_NS   (Interface: $VETH_TX | IP: 192.168.10.1)"
        echo "    - Receiver NS: $RECEIVER_NS (Interface: $VETH_RX | IP: 192.168.10.2)"
        ;;

    down)
        echo "[+] Tearing down network namespaces..."
        ip netns del "$SENDER_NS" 2>/dev/null || true
        ip netns del "$RECEIVER_NS" 2>/dev/null || true
        echo "[✔] Teardown complete. Host networking restored to clean state."
        ;;

    status)
        echo "=== Current Network Namespaces ==="
        ip netns list
        echo ""
        echo "=== Sender Interfaces ==="
        ip netns exec "$SENDER_NS" ip a 2>/dev/null || echo "Namespace $SENDER_NS active: NO"
        echo ""
        echo "=== Receiver Interfaces ==="
        ip netns exec "$RECEIVER_NS" ip a 2>/dev/null || echo "Namespace $RECEIVER_NS active: NO"
        ;;

    *)
        usage
        ;;
esac


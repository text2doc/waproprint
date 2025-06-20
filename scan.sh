#!/bin/bash
echo "=== Informacje o tym urządzeniu ==="
echo "Hostname: $(hostname)"
echo "IP: $(hostname -I)"
echo
echo "=== Skanowanie sieci ==="
nmap -sn $(ip route | grep '192.168' | head -1 | awk '{print $1}' | head -1)
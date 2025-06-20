Pokażę Ci kilka sposobów na sprawdzenie hostów w sieci na Raspberry Pi:

## 1. Sprawdzenie własnej domeny/hosta
```bash
# Sprawdź hostname swojego RPi
hostname

# Sprawdź pełną nazwę domeny
hostname -f

# Sprawdź wszystkie adresy IP
hostname -I
```

## 2. Skanowanie sieci lokalnej

**nmap (najpopularniejsze narzędzie):**
```bash
# Zainstaluj nmap jeśli nie masz
sudo apt install nmap

# Skanuj całą sieć lokalną (przykład dla 192.168.1.0/24)
nmap -sn 192.168.1.0/24

# Bardziej szczegółowe skanowanie
nmap -sS 192.168.1.0/24

# Szybkie skanowanie aktywnych hostów
nmap -sP 192.168.1.0/24
```

**arp-scan:**
```bash
# Zainstaluj arp-scan
sudo apt install arp-scan

# Skanuj sieć lokalną
sudo arp-scan --localnet

# Lub konkretną sieć
sudo arp-scan 192.168.1.0/24
```

## 3. Inne przydatne komendy

```bash
# Sprawdź tablicę ARP (urządzenia, które już komunikowały się z RPi)
arp -a

# Sprawdź routing i interfejsy sieciowe
ip route
ip addr show

# Ping broadcast (może nie działać ze wszystkimi urządzeniami)
ping -b 192.168.1.255

# Netdiscover - pasywne skanowanie
sudo apt install netdiscover
sudo netdiscover -r 192.168.1.0/24
```

## 4. Skrypt do automatycznego skanowania

Możesz utworzyć prosty skrypt:
```bash
#!/bin/bash
echo "=== Informacje o tym urządzeniu ==="
echo "Hostname: $(hostname)"
echo "IP: $(hostname -I)"
echo
echo "=== Skanowanie sieci ==="
nmap -sn $(ip route | grep '192.168' | head -1 | awk '{print $1}' | head -1)
```

Która metoda Cię najbardziej interesuje? Mogę pokazać więcej szczegółów dla konkretnego przypadku użycia.
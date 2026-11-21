#!/bin/bash
#
# fix-peppymeter-timeout.sh - naprawia wiszacy PeppyMeter blokujacy wygaszacz ekranu
#
# PROBLEM (zdiagnozowany 21.11.2026 na px-vol):
#   peppymeterbasic.service ma TimeoutSec=1. Przy koncu albumu plugin wola
#   `systemctl stop peppymeterbasic.service`, systemd wysyla SIGTERM i czeka
#   1 sekunde. PeppyMeter (Python, rysuje meter 800x480) potrzebuje dluzej,
#   wiec systemd anuluje zadanie ("Job for peppymeterbasic.service canceled"),
#   a proces ZOSTAJE na ekranie.
#
#   Skutek: kiosk Chromium nadal wyswietla pelnoekranowy meter zamiast wrocic
#   do menu, wiec ekran nie ma jak sie wygasic. DPMS jest sprawny - po prostu
#   nic nie przywraca wyswietlacza do normalnego stanu.
#
# ROZWIAZANIE: TimeoutSec=1 -> 15 (czas na czyste wyjscie, nadal ograniczony).
#
# Uzycie: fix-peppymeter-timeout.sh [--cofnij]
#
# Uwaga: na px-vol sudo (ALL) ALL wymaga hasla; dostepne sa tylko komendy
# z whitelisty NOPASSWD (m.in. /usr/bin/tee, /bin/systemctl). Dlatego zapis
# idzie przez `sudo -n tee`, nie przez cp/sed -i jako root.

set -uo pipefail

UNIT="/etc/systemd/system/peppymeterbasic.service"
BACKUP_DIR="/home/volumio"
POPRAWNY_TIMEOUT=15

if [ ! -f "$UNIT" ]; then
    echo "BLAD: brak $UNIT" >&2
    exit 1
fi

if [ "${1:-}" = "--cofnij" ]; then
    B=$(ls -t "$BACKUP_DIR"/peppymeterbasic.service.bak-* 2>/dev/null | head -1)
    if [ -z "$B" ]; then
        echo "Brak backupu w $BACKUP_DIR - nie moge cofnac" >&2
        exit 1
    fi
    sudo -n /usr/bin/tee "$UNIT" < "$B" > /dev/null
    sudo -n /bin/systemctl daemon-reload
    echo "Cofnieto z $B"
    grep -E "TimeoutSec" "$UNIT"
    exit 0
fi

# backup (bez sudo - plik jest czytelny)
B="$BACKUP_DIR/peppymeterbasic.service.bak-$(date +%Y%m%d-%H%M%S)"
cp "$UNIT" "$B" 2>/dev/null && echo "backup: $B"

OBECNY=$(grep -oE "^TimeoutSec=[0-9]+" "$UNIT" | cut -d= -f2)
echo "obecny TimeoutSec: ${OBECNY:-brak}"

if [ "${OBECNY:-}" = "$POPRAWNY_TIMEOUT" ]; then
    echo "juz ustawione na $POPRAWNY_TIMEOUT - nic nie robie"
else
    sed "s/^TimeoutSec=.*/TimeoutSec=$POPRAWNY_TIMEOUT/" "$UNIT" \
        | sudo -n /usr/bin/tee "$UNIT" > /dev/null
    sudo -n /bin/systemctl daemon-reload
    echo "ustawiono TimeoutSec=$POPRAWNY_TIMEOUT"
fi

echo
echo "--- weryfikacja ---"
grep -E "TimeoutSec|Restart|ExecStart" "$UNIT"

# test: czy stop faktycznie dziala (cgroup, nie pgrep -f - ten lapie sam siebie)
if systemctl is-active --quiet peppymeterbasic.service; then
    echo
    echo "--- test stopu ---"
    BEFORE=$(systemctl show peppymeterbasic.service -p SubState --value)
    echo "stan przed: $BEFORE"
    sudo -n /bin/systemctl stop peppymeterbasic.service
    sleep 2
    PID=$(systemctl show peppymeterbasic.service -p MainPID --value)
    STATE=$(systemctl show peppymeterbasic.service -p SubState --value)
    echo "stan po:    $STATE (MainPID=$PID)"
    if [ "$PID" = "0" ] && [ "$STATE" = "dead" ]; then
        echo "OK: stop dziala, proces zszedl z ekranu"
    else
        echo "UWAGA: proces nadal zyje - sprawdz recznie"
    fi
else
    echo
    echo "usluga nieaktywna - test stopu pominieto (zostanie uruchomiona przy graniu)"
fi
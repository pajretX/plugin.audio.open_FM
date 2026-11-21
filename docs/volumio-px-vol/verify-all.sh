#!/bin/bash
#
# verify-all.sh - sprawdza czy WSZYSTKIE customizacje px-vol sa na miejscu
#
# Uruchom po restore-all.sh albo w dowolnym momencie, gdy chcesz wiedziec
# czy aktualizacja czegos nie zjadla. Zwraca 0 gdy wszystko OK, 1 gdy sa braki.
#
# Uzycie: /data/volumio-custom/verify-all.sh

set -uo pipefail

OK=0
PROBLEMY=0

ok()   { OK=$((OK+1));       echo "  [OK]   $*"; }
zle()  { PROBLEMY=$((PROBLEMY+1)); echo "  [BRAK] $*"; }
info() { echo "  [info] $*"; }

echo "=========================================="
echo " Weryfikacja customizacji px-vol"
echo " Volumio $(grep -oE 'VOLUMIO_VERSION="[0-9.]+"' /etc/os-release 2>/dev/null | cut -d'"' -f2)"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo

# ---------------------------------------------------------- 1. PeppyMeter
echo "1. PeppyMeter (wygaszacz ekranu)"
UNIT="/etc/systemd/system/peppymeterbasic.service"
if [ -f "$UNIT" ]; then
    T=$(grep -oE "^TimeoutSec=[0-9]+" "$UNIT" | cut -d= -f2)
    [ "${T:-}" = "15" ] && ok "TimeoutSec=15" || zle "TimeoutSec=${T:-brak} (oczekiwane 15) - po stopie albumu Peppy zostanie na ekranie"
    EN=$(systemctl is-enabled peppymeterbasic 2>&1)
    [ "$EN" = "disabled" ] && ok "usluga disabled (startuje na zadanie) - poprawnie" \
                           || info "usluga: $EN"
    # test realnego stopu (cgroup, nie pgrep -f!)
    if systemctl is-active --quiet peppymeterbasic; then
        sudo -n /bin/systemctl stop peppymeterbasic 2>/dev/null
        sleep 2
    fi
    PID=$(systemctl show peppymeterbasic -p MainPID --value 2>/dev/null)
    ST=$(systemctl show peppymeterbasic -p SubState --value 2>/dev/null)
    [ "$PID" = "0" ] && [ "$ST" = "dead" ] && ok "stop dziala (MainPID=0, dead)" \
                                          || zle "stop nie dziala (MainPID=$PID, $ST)"
else
    zle "brak $UNIT"
fi
echo

# --------------------------------------------------------- 2. touch_display
echo "2. touch_display (armowanie DPMS)"
F="/data/plugins/user_interface/touch_display/index.js"
if [ -f "$F" ]; then
    if grep -q "then(self.wakeupScreen.bind(self))" "$F"; then
        ok "armowanie DPMS obecne"
    else
        zle "brak armowania DPMS - ekran moze nie gasnąć do pierwszego dotkniecia"
    fi
else
    zle "brak $F"
fi
echo

# ------------------------------------------------------------- 3. alsacap
echo "3. alsacap (lista urzadzen audio)"
if [ -L /usr/local/bin/alsacap ]; then
    ok "symlink /usr/local/bin/alsacap istnieje"
    if /usr/local/bin/alsacap -C 3 > /dev/null 2>&1; then
        ok "alsacap dziala (karta 3 = HiFiBerry DAC+ Pro)"
    else
        zle "alsacap nie odpowiada"
    fi
else
    zle "brak symlinku /usr/local/bin/alsacap"
fi
echo

# ------------------------------------------------------------- 4. drop-iny
echo "4. Drop-iny systemd"
D="/etc/systemd/system"
for pair in \
    "upmpdcli.service.d/10-wait-config.conf" \
    "upmpdcli.service.d/20-after-mpd.conf" \
    "alsa-restore.service.d/override.conf" \
    "volumio.service.d/override.conf" \
    "bluetooth.service.d/plugins.conf" \
    "bluetooth.service.d/restart.conf" \
    "bluealsa.service.d/restart.conf" ; do
    if [ -f "$D/$pair" ]; then
        ok "$pair"
    else
        zle "$pair"
    fi
done
# czy nie ma zbednych .path (duplikat rozwiazania tego samego problemu)
if ls /etc/systemd/system/*upmpdcli*.path > /dev/null 2>&1; then
    zle "istnieje .path unit dla upmpdcli - DUPLIKAT z drop-inem, moze powodowac petle restartow"
fi
echo

# --------------------------------------------------------------- 5. uslugi
echo "5. Uslugi"
for u in upmpdcli shairport-sync; do
    EN=$(systemctl is-enabled "$u" 2>&1)
    [ "$EN" = "enabled" ] && ok "$u enabled" || zle "$u: $EN"
done
for u in upmpdcli shairport-sync; do
    A=$(systemctl is-active "$u" 2>&1)
    [ "$A" = "active" ] && ok "$u active" || zle "$u: $A"
done
echo

# ------------------------------------------------------------- 6. upmpdcli
echo "6. upmpdcli - openhome"
if [ -f /tmp/upmpdcli.conf ]; then
    OH=$(grep -oE "^openhome *= *[0-9]+" /tmp/upmpdcli.conf | grep -oE "[0-9]+$")
    [ "${OH:-}" = "0" ] && ok "openhome = 0 (Symfonium: pozycja nie zamarznie)" \
                        || zle "openhome = ${OH:-nie ustawione} (oczekiwane 0)"
else
    zle "brak /tmp/upmpdcli.conf"
fi
echo

# --------------------------------------------------------------- 7. DPMS
echo "7. DPMS (wygaszanie panelu)"
if [ -f /home/volumio/.Xauthority ]; then
    WY=$(XAUTHORITY=/home/volumio/.Xauthority sudo -n /usr/bin/xset -display :0 q 2>/dev/null)
    if [ -n "$WY" ]; then
        OFF=$(echo "$WY" | grep -oE "Off: [0-9]+")
        DPMS=$(echo "$WY" | grep -oE "DPMS is (Enabled|Disabled)")
        echo "$DPMS" | grep -q Enabled && ok "$DPMS" || zle "$DPMS"
        echo "  [info] $OFF"
        echo "  [info] (Off: 120 = gaszenie po 120s; Off: 0 przy 'play' jest poprawne - ekran trzymany)"
    else
        info "nie udalo sie odczytac DPMS (brak dostepu do X11?)"
    fi
else
    info "brak /home/volumio/.Xauthority - pomijam test DPMS"
fi
echo

# ------------------------------------------------------------- 8. konfigi
echo "8. Konfiguracja pluginow"
CFG="/data/configuration/user_interface/touch_display/config.json"
if [ -f "$CFG" ]; then
    TOUT=$(grep -oE '"timeout":\{"type":"number","value":[0-9]+' "$CFG" | grep -oE '[0-9]+$')
    APLAY=$(grep -oE '"afterPlay":\{"type":"boolean","value":(true|false)' "$CFG" | grep -oE '(true|false)$')
    [ "$TOUT" = "120" ] && [ "$APLAY" = "true" ] \
        && ok "touch_display: timeout=120, afterPlay=true" \
        || zle "touch_display: timeout=$TOUT afterPlay=$APLAY (oczekiwane 120/true)"
fi
PCFG="/data/configuration/user_interface/peppymeterbasic/config.json"
if [ -f "$PCFG" ]; then
    MET=$(grep -oE '"meter":\{"type":"string","value":"[^"]*"' "$PCFG" | grep -oE '"[^"]*"$')
    ok "peppymeterbasic: meter=$MET"
fi
echo

# -------------------------------------------------------------- 9. pluginy
echo "9. Pluginy - obecnosc katalogow"
for p in "user_interface/touch_display" "user_interface/peppymeterbasic" "music_service/openfm" "music_service/spop" "music_service/youtube2"; do
    [ -d "/data/plugins/$p" ] && ok "$p" || zle "$p (brak - plugin do reinstalacji)"
done
echo

# -------------------------------------------------- 10. openfm - edycje
echo "10. openfm - rozszerzenia kodu"
OF="/data/plugins/music_service/openfm/index.js"
if [ -f "$OF" ]; then
    if grep -q "API_STANDALONE" "$OF" && grep -q "_categoryStationsCache" "$OF"; then
        ok "rozszerzenia obecne (API_STANDALONE, cache kategorii)"
    else
        zle "rozszerzenia BRAK - plugin zostal nadpisany przez Update, odtworz z repo pajretX/plugin.audio.open_FM"
    fi
else
    zle "brak $OF"
fi
echo

echo "=========================================="
echo " OK: $OK   PROBLEMY: $PROBLEMY"
if [ "$PROBLEMY" -eq 0 ]; then
    echo " Wszystkie customizacje na miejscu."
else
    echo " Uruchom: /data/volumio-custom/restore-all.sh"
fi
echo "=========================================="

exit $([ "$PROBLEMY" -gt 0 ] && echo 1 || echo 0)
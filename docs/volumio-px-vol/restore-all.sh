#!/bin/bash
#
# restore-all.sh - odtwarza WSZYSTKIE customizacje px-vol po aktualizacji Volumio
#
# Uruchom po kazdej aktualizacji systemu Volumio ORAZ po kazdym "Plugin Update"
# z UI. Idempotentny - mozna uruchamiac wielokrotnie.
#
# Uzycie:  /data/volumio-custom/restore-all.sh
#          /data/volumio-custom/restore-all.sh --dry-run   (tylko pokaz co zrobi)
#
# sudo na px-vol: (ALL) ALL wymaga hasla, wiec uzywamy wylacznie komend
# z whitelisty NOPASSWD (/usr/bin/tee, /bin/systemctl, /bin/ln, /bin/mkdir).

set -uo pipefail

DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

CUSTOM="/data/volumio-custom"
ZMIANY=0
BLEDY=0

log()  { echo "[restore] $*"; }
zmiana() { ZMIANY=$((ZMIANY+1)); log "ZMIENIONO: $*"; }
blad()  { BLEDY=$((BLEDY+1)); echo "[restore][BLAD] $*" >&2; }

zapisz_root() {
    # $1 = sciezka docelowa, stdin = zawartosc
    local cel="$1"
    if [ "$DRY" = "1" ]; then
        echo "[restore] (dry-run) zapisalby: $cel"
        return 0
    fi
    sudo -n /usr/bin/tee "$cel" > /dev/null || { blad "zapis $cel"; return 1; }
}

# ============================================================ 1. PeppyMeter
fix_peppymeter() {
    local UNIT="/etc/systemd/system/peppymeterbasic.service"
    [ -f "$UNIT" ] || { blad "brak $UNIT"; return 1; }

    local T
    T=$(grep -oE "^TimeoutSec=[0-9]+" "$UNIT" | cut -d= -f2)
    if [ "${T:-}" = "15" ]; then
        log "1. PeppyMeter TimeoutSec=15 - OK"
        return 0
    fi

    log "1. PeppyMeter TimeoutSec: ${T:-brak} -> 15"
    if [ "$DRY" = "0" ]; then
        cp "$UNIT" "/home/volumio/peppymeterbasic.service.bak-$(date +%Y%m%d-%H%M%S)" 2>/dev/null
        sed "s/^TimeoutSec=.*/TimeoutSec=15/" "$UNIT" | zapisz_root "$UNIT"
        sudo -n /bin/systemctl daemon-reload
    fi
    zmiana "peppymeterbasic.service TimeoutSec=15"
}

# ========================================================== 2. touch_display
fix_touch_display() {
    local F="/data/plugins/user_interface/touch_display/index.js"
    [ -f "$F" ] || { blad "brak $F (plugin touch_display nie zainstalowany?)"; return 1; }

    # czy juz ma armowanie DPMS (.then(wakeupScreen) po setScreenTimeout w init)?
    if grep -q "setScreenTimeout(self.config.get('timeout'), false)" "$F" && \
       grep -A1 "setScreenTimeout(self.config.get('timeout'), false)" "$F" | grep -q "then(self.wakeupScreen"; then
        log "2. touch_display - armowanie DPMS obecne, OK"
        return 0
    fi

    log "2. touch_display - brak armowania DPMS, dodaje"
    if [ "$DRY" = "0" ]; then
        if [ -x "$CUSTOM/fix-touch-display.py" ]; then
            if ! "$CUSTOM/fix-touch-display.py" "$F"; then
                blad "nie udalo sie naprawic touch_display"
                return 1
            fi
        else
            blad "brak $CUSTOM/fix-touch-display.py"
            return 1
        fi
    fi
    zmiana "touch_display/index.js - armowanie DPMS"
    log "   UWAGA: wymaga restartu volumio: volumio vrestart"
}

# ================================================================ 3. alsacap
fix_alsacap() {
    if [ -L /usr/local/bin/alsacap ]; then
        log "3. symlink alsacap - OK"
        return 0
    fi
    log "3. symlink alsacap brakuje, tworze"
    [ "$DRY" = "0" ] && sudo -n /bin/ln -sf /usr/bin/alsacap /usr/local/bin/alsacap
    zmiana "/usr/local/bin/alsacap -> /usr/bin/alsacap"
}

# ============================================================= 4. drop-iny
fix_dropiny() {
    local D="/etc/systemd/system"
    local POTRZEBA=0

    utworz() {  # $1=sciezka $2=zawartosc
        local cel="$1"
        # Porownanie przez plik tymczasowy, nie przez $(cat) - command substitution
        # gubi koncowe znaki nowej linii i daje falszywe "rozni sie".
        local tmp
        tmp=$(mktemp)
        printf '%s' "$2" > "$tmp"
        if [ -f "$cel" ] && cmp -s "$tmp" "$cel"; then
            rm -f "$tmp"
            return 0   # juz identyczne
        fi
        rm -f "$tmp"
        log "4. drop-in: $cel"
        if [ "$DRY" = "0" ]; then
            sudo -n /bin/mkdir -p "$(dirname "$cel")"
            printf '%s' "$2" | zapisz_root "$cel"
        fi
        zmiana "drop-in $(basename "$(dirname "$cel")")/$(basename "$cel")"
        POTRZEBA=1
    }

    utworz "$D/upmpdcli.service.d/10-wait-config.conf" '[Service]
ExecStartPre=/bin/sh -c "for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do [ -f /tmp/upmpdcli.conf ] && break; sleep 2; done; sed -i '"'"'s/^openhome *= *1/openhome = 0/'"'"' /tmp/upmpdcli.conf; exit 0"
'

    utworz "$D/upmpdcli.service.d/20-after-mpd.conf" '[Unit]
After=mpd.service
Wants=mpd.service
'

    utworz "$D/alsa-restore.service.d/override.conf" '[Service]
ExecStartPre=/bin/mkdir -p /run/alsa /run/alsa/runtime
ExecStartPre=/usr/bin/wait-for-cards.sh
'

    utworz "$D/volumio.service.d/override.conf" '[Unit]
After=alsa-restore.service
Requires=alsa-restore.service
'

    utworz "$D/bluetooth.service.d/plugins.conf" '[Service]
ExecStart=
ExecStart=/usr/libexec/bluetooth/bluetoothd --noplugin=sap,battery,midi,wiimote,scanparam,ccp
'

    utworz "$D/bluetooth.service.d/restart.conf" '[Unit]
Wants=bluealsa.service

[Service]
Restart=on-failure
'

    utworz "$D/bluealsa.service.d/restart.conf" '[Unit]
PartOf=bluetooth.service
'

    if [ "$POTRZEBA" = "1" ] && [ "$DRY" = "0" ]; then
        sudo -n /bin/systemctl daemon-reload
        log "   daemon-reload wykonany"
    else
        log "4. drop-iny systemd - wszystkie OK"
    fi
}

# ============================================================== 5. konfigi
sprawdz_konfigi() {
    local CFG="/data/configuration/user_interface/touch_display/config.json"
    if [ -f "$CFG" ]; then
        local TOUT APLAY
        TOUT=$(grep -oE '"timeout":\{"type":"number","value":[0-9]+' "$CFG" | grep -oE '[0-9]+$')
        APLAY=$(grep -oE '"afterPlay":\{"type":"boolean","value":(true|false)' "$CFG" | grep -oE '(true|false)$')
        if [ "$TOUT" = "120" ] && [ "$APLAY" = "true" ]; then
            log "5. touch_display config (timeout=120, afterPlay=true) - OK"
        else
            echo "[restore][UWAGA] touch_display config: timeout=$TOUT afterPlay=$APLAY (oczekiwane 120/true)"
            blad "config touch_display wymaga recznej korekty w UI"
        fi
    fi
}

# ================================================================== main
echo "=========================================="
echo " Restore customizacji px-vol"
echo " Volumio $(grep -oE 'VOLUMIO_VERSION="[0-9.]+"' /etc/os-release 2>/dev/null | cut -d'"' -f2)"
echo " $(date '+%Y-%m-%d %H:%M:%S')"
[ "$DRY" = "1" ] && echo " *** TRYB DRY-RUN - nic nie zmieniam ***"
echo "=========================================="
echo

fix_peppymeter
fix_touch_display
fix_alsacap
fix_dropiny
sprawdz_konfigi

echo
echo "=========================================="
echo " Zmian: $ZMIANY   Bledy: $BLEDY"
echo "=========================================="

if [ "$ZMIANY" -gt 0 ] && [ "$DRY" = "0" ]; then
    echo
    echo "Teraz uruchom:  volumio vrestart"
    echo "potem sprawdz:  /data/volumio-custom/verify-all.sh"
fi

exit $([ "$BLEDY" -gt 0 ] && echo 1 || echo 0)
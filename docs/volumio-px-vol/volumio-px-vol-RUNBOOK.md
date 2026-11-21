# Volumio px-vol — Runbook odtworzenia po aktualizacji

**Urządzenie:** px-vol (RPi 4, HiFiBerry DAC+ Pro) — `192.168.1.222`, SSH: `ssh -i /opt/data/.ssh/volumio volumio@192.168.1.222`
**Stan bazowy:** Volumio **4.231** / Debian 12 bookworm / `VOLUMIO_HASH=43f53a1f9ad8f3b898137f70f5cd23ce`
**Data inwentaryzacji:** 21.11.2026

> **Kolejność po aktualizacji:** uruchom `restore-all.sh` → zweryfikuj `verify-all.sh` → dopiero potem testuj odtwarzanie.
> Skrypty są w `/data/volumio-custom/` na urządzeniu (katalog `/data` przeżywa OTA).

---

## Co przetrwa aktualizację, a co nie

| Ścieżka | OTA systemu | Plugin Update (UI) |
|---|---|---|
| `/data/configuration/**` | ✅ przeżywa | ✅ przeżywa |
| `/data/plugins/**` | ✅ przeżywa | ❌ **kasowane** |
| `/etc/systemd/system/**` | ✅ przeżywa | ✅ przeżywa |
| `/usr/local/bin/**`, `/usr/bin/**` | ✅ przeżywa | ✅ przeżywa |
| `/volumio/app/**` | ❌ **kasowane (hash gate)** | ✅ przeżywa |
| `/home/volumio/**` | ✅ przeżywa | ✅ przeżywa |

**Nie klikaj „Update"/„Reinstall" na pluginie w UI** bez uprzedniego uruchomienia `backup-plugins.sh` — nadpisze `/data/plugins/<kat>/<nazwa>/` i skasuje edycje kodu.

---

## 1. PeppyMeter blokuje wygaszacz — `TimeoutSec=1`

**Plik:** `/etc/systemd/system/peppymeterbasic.service`
**Zmiana:** `TimeoutSec=1` → **`TimeoutSec=15`**

**Objaw:** po zakończeniu albumu PeppyMeter zostaje na ekranie zamiast wrócić do menu; ekran nie gaśnie.
**Przyczyna:** systemd daje procesowi 1 s na SIGTERM; Python rysujący meter nie zdąży → `Job for peppymeterbasic.service canceled` → proces zostaje na ekranie. Dopóki meter wisi, DPMS nie ma czego wygasić (sam DPMS jest sprawny).
**Uwaga:** usługa jest `disabled` i startowana na żądanie przez plugin — **nie włączaj** (`enable`) jej.

```bash
sudo -n /usr/bin/tee /etc/systemd/system/peppymeterbasic.service <<'EOF'
[Unit]
Description=peppymeterbasic Daemon 
After=syslog.target
[Service]
Type=simple
WorkingDirectory=/data/plugins/user_interface/peppymeterbasic
ExecStart=/data/plugins/user_interface/peppymeterbasic/startpeppymeterbasic.sh
Restart=no
SyslogIdentifier=volumio
User=volumio
Group=volumio
TimeoutSec=15
[Install]
WantedBy=multi-user.target
EOF
sudo -n /bin/systemctl daemon-reload
```

**Weryfikacja:** `systemctl show peppymeterbasic.service -p MainPID -p ActiveState -p SubState` → po stopie `MainPID=0`, `inactive`, `dead`.
Skrypt: `/data/volumio-custom/fix-peppymeter-timeout.sh` (z `--cofnij`).

---

## 2. touch_display — armowanie DPMS przy starcie

**Plik:** `/data/plugins/user_interface/touch_display/index.js` (ok. linia 1600) — **kasowany przez Plugin Update**

**Zmiana:** po inicjalnym `setScreenTimeout` doszło `.then(self.wakeupScreen.bind(self))`:

```js
// BYŁO:
self.setScreenTimeout(self.config.get('timeout'), false);

// JEST:
self.setScreenTimeout(self.config.get('timeout'), false)
.then(self.wakeupScreen.bind(self));
```

**Po co:** ustawienie timeoutu DPMS nie uzbraja licznika bezczynności — ekran potrafi świecić w nieskończoność do pierwszego dotknięcia. `xset dpms force on` uzbraja licznik, a przy starcie ekran jest już włączony, więc jest to wizualnie neutralne. Efekt: blanking działa od bootu, bez budzenia przy przejściu play→stop.

**Weryfikacja:** `XAUTHORITY=/home/volumio/.Xauthority sudo -n /usr/bin/xset -display :0 q` → `DPMS is Enabled`, `Off: 120`, a przy `status: play` → `Off: 0`.

---

## 3. upmpdcli — `openhome = 0` + kolejność startu

**Plik A (kasowany przez OTA):** `/volumio/app/plugins/audio_interface/upnp/upmpdcli.conf.tmpl` → `openhome = 1` na `openhome = 0`

**Po co:** upmpdcli z `openhome = 1` reklamuje OpenHome, a klienty Android (Symfonium) wolą OpenHome — jego raportowanie pozycji **zawiesza się** na strumieniach FLAC z Jellyfina (pasek postępu i tekst stoją, choć audio gra). UPnP AV czyta pozycję wprost z MPD i działa poprawnie.

**LEPIEJ: nie edytuj `/volumio` ręcznie** (łamie hash gate i blokuje OTA). Poprawnie robi to drop-in w punkcie 4 — on wymusza `openhome = 0` przy każdym starcie.

**Weryfikacja:** `grep '^openhome' /tmp/upmpdcli.conf` → `openhome = 0`

---

## 4. Drop-iny systemd (przetrwają wszystko — najważniejsze)

Wszystkie w `/etc/systemd/system/<unit>.service.d/`. **Nie kasuj ich i nie dodawaj drugiego rozwiązania tego samego problemu** (dwa naraz = pętla restartów).

### 4.1 `upmpdcli.service.d/10-wait-config.conf`
Czeka na `/tmp/upmpdcli.conf` (tworzy go plugin Volumio przy starcie) i wymusza `openhome = 0`:
```ini
[Service]
ExecStartPre=/bin/sh -c "for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do [ -f /tmp/upmpdcli.conf ] && break; sleep 2; done; sed -i 's/^openhome *= *1/openhome = 0/' /tmp/upmpdcli.conf; exit 0"
```
**Po co:** `upmpdcli.service` startuje PRZED wygenerowaniem konfiguracji → bez tego crash-loop („Could not open config") i renderer niewidoczny dla kontrolerów.

### 4.2 `upmpdcli.service.d/20-after-mpd.conf`
```ini
[Unit]
After=mpd.service
Wants=mpd.service
```

### 4.3 `alsa-restore.service.d/override.conf`
```ini
[Service]
ExecStartPre=/bin/mkdir -p /run/alsa /run/alsa/runtime
ExecStartPre=/usr/bin/wait-for-cards.sh
```

### 4.4 `volumio.service.d/override.conf`
```ini
[Unit]
After=alsa-restore.service
Requires=alsa-restore.service
```

### 4.5 `bluetooth.service.d/plugins.conf`
```ini
[Service]
ExecStart=
ExecStart=/usr/libexec/bluetooth/bluetoothd --noplugin=sap,battery,midi,wiimote,scanparam,ccp
```

### 4.6 `bluetooth.service.d/restart.conf`
```ini
[Unit]
Wants=bluealsa.service

[Service]
Restart=on-failure
```

### 4.7 `bluealsa.service.d/restart.conf`
```ini
[Unit]
PartOf=bluetooth.service
```

---

## 5. Symlink alsacap (naprawia błąd „Cannot read Audio Device Capabilities")

```bash
sudo -n /bin/ln -sf /usr/bin/alsacap /usr/local/bin/alsacap
```
Volumio szuka binarki w `/usr/local/bin`, a jest w `/usr/bin` → lista urządzeń wyjściowych nie działa (odtwarzanie działa).
**Weryfikacja:** `/usr/local/bin/alsacap -C 3` (HiFiBerry DAC+ Pro = karta 3, Loopback = 7).

---

## 6. Konfiguracja pluginów (w `/data` — przeżywa, ale zapisz dla odtworzenia)

### touch_display — `/data/configuration/user_interface/touch_display/config.json`
Kluczowe wartości:
- `timeout: 120` — wygaszanie po 120 s bezczynności
- `afterPlay: true` — nie gaś podczas grania, licznik startuje po stopie
- `virtualKeyboard: true`
- `pluginVersion: 3.6.0`

### peppymeterbasic — `/data/configuration/user_interface/peppymeterbasic/config.json`
- `meter: bar`, `screensize: 800x480`, `metersize: 30`, `autosize: true`, `delaymeter: 20`

### openfm — edycje kodu (kasowane przez Plugin Update!)
`/data/plugins/music_service/openfm/index.js` ma rozszerzenia ponad `.bak`:
- stałe `API_STANDALONE`, `API_CATEGORIES`, `API_CATEGORY_PREFIX`
- cache kategorii (`_categoryStationsCache`, `_categoryStationsCacheTime`)
- równoległe pobieranie stacji + standalone przez `libQ.all`
- **To jest kod Twojego pluginu open_FM** — źródło prawdy jest w repo GitHub `pajretX/plugin.audio.open_FM`, nie na urządzeniu. Po aktualizacji: sklonuj repo, popraw, `volumio plugin install`.

---

## 7. Znane pułapki (żeby nie tracić na nie czasu drugi raz)

- **Nigdy nie uruchamiaj `git` w `/volumio`** — `.git` jest w haszowanym drzewie; `git status` zmienia `.git/index` i **blokuje aktualizacje bez żadnej intencjonalnej edycji**.
- **`pgrep -f peppymeter.py` łapie własny proces sprawdzający** i fałszywie raportuje „proces nadal żyje". Używaj `systemctl show <unit> -p MainPID -p SubState`.
- **`Screen Saver: timeout: 0` jest nieistotny** — panelem DSI steruje DPMS (`Off: N`). Nie „naprawiaj" zera w screen saverze.
- **upmpdcli/libupnpp zwraca puste odpowiedzi (HTTP 000)** na `localhost`/127.0.0.1 nawet gdy działa — testuj przez `curl http://192.168.1.222:49152/...`. Deskryptor nie jest pod `/description.xml`, tylko `/uuid-<id>/description.xml`.
- **`sudo` na px-vol:** `(ALL) ALL` wymaga hasła, `sudo -S` z hasłem jest blokowane. Dostępne bez hasła: `/usr/bin/tee`, `/bin/systemctl`, `/bin/journalctl`, `/bin/rm`, `/bin/mv`, `/bin/ln`, `/usr/bin/xset`, `/usr/bin/apt-get`, `/usr/bin/killall`, `/sbin/reboot`, `/usr/bin/timedatectl` i inne — patrz `sudo -n -l`. Pisz pliki przez `printf ... | sudo -n /usr/bin/tee <ścieżka>`.
- **Kontrola integralności OTA:** Volumio haszuje całe `/volumio` i odmawia aktualizacji przy każdej różnicy. Obejście jednorazowe: `touch /data/ignoresystemcheck`. Preferuj realną naprawę (przenieś zmianę do `/etc` lub `/data`).
- **Panel ciemny ≠ wyłączony.** Sprawdzaj `/sys/class/backlight/*/bl_power` (0 = wyłączony) obok `brightness` (0-255).

---

## 8. Kopia zapasowa

`/mnt/cache/backups/vmail` — **NIE DOTYKAĆ** (backup poczty krawczyk.ninja).

Backup konfiguracji Volumio: `backup-all.sh` w `/data/volumio-custom/` tworzy archiwum tego katalogu + configów pluginów w `/data/volumio-custom/backups/`.
Kopia zdalna na Unraid: `/mnt/user/backups/volumio-px-vol/` (pull przez `scp`).
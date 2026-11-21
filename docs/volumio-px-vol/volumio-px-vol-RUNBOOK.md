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

### openfm — wersja Volumio (JS). NIE mylić z Kodi (Python)!

**To są DWIE OSOBNE IMPLEMENTACJE tego samego serwisu open.fm. Nie mieszaj ich nigdy.**

| | Volumio (px-vol) | Kodi (laptop) |
|---|---|---|
| język | JavaScript | Python 3 |
| plik | `index.js` | `default.py` + `resources/lib/*.py` |
| lokalizacja | `/data/plugins/music_service/openfm/` | Kodi addon `plugin.audio.open_FM` |
| wersja | 1.0.4 | 3.1.0 |
| repo | `pajretX/volumio-plugins-sources-bookworm` | `pajretX/plugin.audio.open_FM` |
| gałąź | **`openfm-submit`** | `master` |
| katalog | `openfm/` | katalog główny repo |

**Odtworzenie wersji Volumio po aktualizacji pluginu:**
```bash
git clone --depth 1 --branch openfm-submit \
  git@github.com:pajretX/volumio-plugins-sources-bookworm.git
# plugin jest w katalogu openfm/
```

**Porównanie wersji (lokalna vs GitHub) — ZAWSZE przez normalizację CRLF:**

Volumio serwuje pliki z `\r\n`, GitHub trzyma `\n`. Surowy rozmiar różni się o liczbę linii (885 B dla 885 linii) i **nie oznacza zmiany treści**. Porównuj tak:
```bash
tr -d '\r' < index.js | md5sum
# oczekiwane dla 1.0.4: 7050947058070c827ec737e4d151ed3b
```
Nigdy nie wnioskuj o rozjeździe wersji z samej różnicy rozmiaru pliku.

**Naprawy zawarte w wersji Volumio 1.0.4** (ponad stan bez tych zmian):
- stacje **standalone** (`API_STANDALONE`, równolegle przez `libQ.all`, `.fail()` → `'[]'`)
- **pełne listy stacji w kategoriach** (`getCategoryStations(slug)` → `/api/radio/category/<slug>` + cache TTL) — wcześniej kategoria pokazywała ~5 stacji
- **kategorie z API** (`/api/radio/categories`), scraping HTML `__NEXT_DATA__` **zachowany jako fallback**
- **Premium**: dopisek `[Premium]`, gwiazdka `fa fa-star`, **odrzucenie odtwarzania z toastem** (PL/EN)
- metadata reader `timed_id3` **tylko dla `.m3u8`** — dla AAC standalone nie odpala (oszczędza CPU)
- guard w `getStreamUrl` — URL spoza `stream-cdn-1.open.fm` i bez `.m3u8` zwracany bez tokenowania

**Uwaga o parzystości z Kodi:** `default.py` (Kodi 3.1.0) ma standalone i pełne kategorie z API, ale Premium tylko jako dopisek `[Premium]` do nazwy — **bez odrzucania odtwarzania i bez ikony gwiazdki**. To jedyna znana asymetria między implementacjami. Nie opisuj wersji Kodi jako „nieobsługującej Premium" — ona oznacza Premium tekstowo.

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

## 8. Zasady ustalania faktów (obowiązkowe przed każdym twierdzeniem)

Ta sekcja istnieje, bo 21.11.2026 wprowadziłem użytkownika w błąd **trzy razy w jednej rozmowie**, opierając się na niepełnym rozpoznaniu. Każdy błąd byłby uniknięty jednym zapytaniem. Zasady są twarde, nie są sugestiami.

### 8.1. Zanim twierdzisz, że czegoś nie ma — sprawdź WSZYSTKIE gałęzie i wszystkie repo

```bash
# 1) wszystkie repo uzytkownika
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/user/repos?per_page=100" | jq -r '.[].name'

# 2) WSZYSTKIE galezie danego repo (nie tylko master!)
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/<user>/<repo>/branches?per_page=100" | jq -r '.[].name'

# 3) plik na konkretnej galezi
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/<user>/<repo>/contents/<katalog>?ref=<galeza>"
```

**Rzeczywisty błąd, którego to dotyczy:** twierdziłem, że repo `plugin.audio.open_FM` nie zawiera wersji Volumio — sprawdziłem tylko `master`. Wersja JS leżała na **gałęzi `openfm-submit` w innym repo** (`volumio-plugins-sources-bookworm`). Zanim powiesz „brak" — pytaj API o gałęzie.

### 8.2. Nie mieszaj implementacji różnych platform

Volumio = JavaScript. Kodi = Python. To **dwa osobne projekty na tym samym API open.fm**, w dwóch osobnych repo. Rozmawiając o Volumio, patrz wyłącznie na `index.js` i `volumio-plugins-sources-bookworm`. Rozmawiając o Kodim — na `default.py` i `plugin.audio.open_FM`. Nigdy nie przenoś wniosku z jednej na drugą.

### 8.3. Różnica rozmiaru pliku to NIE różnica treści (CRLF)

Volumio serwuje `\r\n`, GitHub trzyma `\n`. Różnica = liczba linii w bajtach. Zawsze normalizuj przed porównaniem:
```bash
tr -d '\r' < plik | md5sum
```
Nie ogłaszaj „wersje się rozjechały", dopóki md5 po normalizacji się nie różni.

### 8.4. Każdy wynik `grep` weryfikuj osobno — nie ufaj złożonym pipeline'om

Mój `grep -ci premium` zwrócił `0` przy **faktycznym trafieniu** w linii 46, bo poprzednia gałąź polecenia wypisała `0` i wziąłem to za wynik. Potem ogłosiłem „Kodi nie obsługuje Premium" — nieprawda.
```bash
# ZLE: wynik moze pochodzic z innej galezi niz myslisz
for p in a b; do grep -ci "$p" plik || echo 0; done

# DOBRZE: osobne polecenie, widoczny kontekst
grep -n "premium" plik; echo "exit=$?"
```
Przy wyniku `0` **zawsze** potwierdź niezależnym poleceniem (`grep -n`), że naprawdę nie ma trafień.

### 8.5. Rozróżniaj „naprawiłem błąd" od „dodałem funkcję"

Przed opisaniem własnej zmiany jako „poprawki" — przeczytaj diff i powiedz, czy usuwała usterkę, czy dodawała możliwość. 21.11 nazwałem 135 linii dodanych kodu „poprawkami openfm", sugerując że coś było zepsute. Nie było — to była rozbudowa funkcjonalna. Użytkownik ma prawo wiedzieć, co dokładnie zmieniono i dlaczego.

### 8.6. Gdy użytkownik mówi „to już istnieje" — ma prawie zawsze rację

Jeśli user zaprzecza faktowi, który podałem, **najpierw szukam dowodów przeciw sobie**, nie bronię tezy. Dwukrotnie w tej rozmowie user miał rację („przecież tam było logo", „mamy już repo dla volumio i openfm"), a ja się myliłem.

### 8.7. Zanim zaproponuję „nowe rozwiązanie" — sprawdź, czy nie istnieje

Proponowałem „osobne repo dla index.js" oraz „wrzucić index.js do repo". Oba były zbędne — plugin był na GitHubie od 17.11. Zanim zaproponujesz pracę, sprawdź stan faktyczny. Propozycja czegoś, co jest już wykonane, kosztuje zaufanie i czas.

### 8.8. Weryfikuj stan faktyczny przed raportem, nie po

Każde twierdzenie o stanie systemu musi być poparte poleceniem wykonanym **w tej samej sesji**. Nie polegaj na notatkach, skillach ani pamięci — one opisują stan z przeszłości. Przykład: `wc -c` pokazał różnicę 885 B i prawie ogłosiłem rozjazd wersji; jedno `md5sum` po normalizacji to rozstrzygnęło.

**Test prosty:** czy umiem wskazać polecenie z tej sesji, które potwierdza to zdanie? Jeśli nie — nie piszę tego zdania.

---

## 9. Kopia zapasowa

`/mnt/cache/backups/vmail` — **NIE DOTYKAĆ** (backup poczty krawczyk.ninja).

Backup konfiguracji Volumio: `backup-all.sh` w `/data/volumio-custom/` tworzy archiwum tego katalogu + configów pluginów w `/data/volumio-custom/backups/`.
Kopia zdalna na Unraid: `/mnt/user/backups/volumio-px-vol/` (pull przez `scp`).
# px-vol — customizacje Volumio

Runbook odtworzenia niestandardowych poprawek na urządzeniu Volumio **px-vol**
(RPi 4 + HiFiBerry DAC+ Pro, Volumio 4.231), które giną przy aktualizacji
systemu lub przy „Plugin Update" z UI.

## Szybki start po aktualizacji

Na urządzeniu (skrypty leżą w `/data/volumio-custom/`, katalog `/data` przeżywa OTA):

```bash
/data/volumio-custom/restore-all.sh    # odtwórz wszystko
volumio vrestart                       # przeładuj wtyczki
/data/volumio-custom/verify-all.sh     # sprawdź 27 punktów kontrolnych
```

Zdalnie z Hermesa (Unraid), gdy `/data` zostało wyczyszczone:

```bash
scp -i /opt/data/.ssh/volumio restore-all.sh verify-all.sh fix-touch-display.py \
    volumio@192.168.1.222:/data/volumio-custom/
```

## Zawartość

| Plik | Rola |
|---|---|
| `volumio-px-vol-RUNBOOK.md` | **Pełna dokumentacja** wszystkich poprawek, przyczyn i pułapek |
| `restore-all.sh` | Odtwarza wszystkie customizacje (idempotentny, `--dry-run`) |
| `verify-all.sh` | 27 kontroli stanu; exit 1 gdy braki |
| `fix-touch-display.py` | Dodaje armowanie DPMS w pluginie touch_display (1:1) |
| `fix-peppymeter-timeout.sh` | Naprawia `TimeoutSec` PeppyMetera (`--cofnij`) |

## Czego pilnować

- **Nie klikać „Update"/„Reinstall"** na pluginie w UI — nadpisze `/data/plugins/**`.
- **Nie uruchamiać `git` w `/volumio`** — `.git` jest w haszowanym drzewie i blokuje OTA.
- **Nie kasować drop-inów systemd** ani dodawać drugiego rozwiązania tego samego problemu.

Testowane: symulacja pełnej aktualizacji (10 zniszczonych poprawek) → `restore-all.sh`
→ 27/27 OK, pliki odtworzone bit w bit.

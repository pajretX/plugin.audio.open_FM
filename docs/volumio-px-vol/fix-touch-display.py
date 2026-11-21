#!/usr/bin/env python3
"""
fix-touch-display.py - dodaje armowanie DPMS w pluginie touch_display

PROBLEM (zdiagnozowany na px-vol):
  Ustawienie timeoutu DPMS nie uzbraja licznika bezczynnosci - ekran potrafi
  swiecic w nieskonczonosc, dopoki nie dotkniesz panelu. `xset dpms force on`
  UZBRAJA licznik. Przy starcie ekran jest juz wlaczony, wiec jest to wizualnie
  neutralne.

ZMIANA:
  W init (blok .on('ready') -> else) po setScreenTimeout dopisujemy:
      .then(self.wakeupScreen.bind(self));

  BYLO:
      self.setScreenTimeout(self.config.get('timeout'), false)
                          (lub ...false); )
  MA BYC:
      self.setScreenTimeout(self.config.get('timeout'), false)
            .then(self.wakeupScreen.bind(self));

Odporny na oba warianty zakonczenia (z `;` i bez), bo plik bywa edytowany
recznie i w roznych wersjach pluginu ma inny terminator.

Uzycie: fix-touch-display.py <sciezka-do-index.js> [--dry-run]
Zwraca 0 gdy OK (lub juz naprawione), 1 przy bledzie.
"""

import sys
import re

DRY = "--dry-run" in sys.argv
args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    print("Uzycie: fix-touch-display.py <index.js> [--dry-run]", file=sys.stderr)
    sys.exit(1)

sciezka = args[0]

try:
    with open(sciezka, encoding="utf-8", errors="surrogateescape") as f:
        tresc = f.read()
except OSError as e:
    print(f"BLAD: nie moge czytac {sciezka}: {e}", file=sys.stderr)
    sys.exit(1)

# juz naprawione?
if "then(self.wakeupScreen.bind(self))" in tresc:
    print("juz naprawione - armowanie DPMS obecne")
    sys.exit(0)

# Szukamy wywolania setScreenTimeout w galezi 'else' bloku init.
# Terminator moze byc `;` albo brak (po recznej edycji).
wzorzec = re.compile(
    r"(self\.setScreenTimeout\(self\.config\.get\('timeout'\), false\))(;?)"
)

trafienia = list(wzorzec.finditer(tresc))
if not trafienia:
    print("BLAD: nie znalazlem wywolania setScreenTimeout w oczekiwanej formie",
          file=sys.stderr)
    sys.exit(1)

# Bierzemy OSTATNIE trafienie - w init jest po nim m.in. initHDMIAudio,
# a wczesniejsze wystapienia (o ile sa) dotycza innych sciezek.
m = trafienia[-1]

# Zachowujemy oryginalne wciecie linii
poczatek_linii = tresc.rfind("\n", 0, m.start()) + 1
wciecie = tresc[poczatek_linii:m.start()]

zamiana = (
    m.group(1)
    + "\n"
    + wciecie                                  # dokladnie to samo wciecie co linia wyzej
    + ".then(self.wakeupScreen.bind(self));"
)

nowa = tresc[:m.start()] + zamiana + tresc[m.end():]

print(f"znaleziono wywolanie w linii {tresc[:m.start()].count(chr(10)) + 1}")

if DRY:
    print("--- dry-run, nie zapisuje ---")
    print("byloby:")
    print(zamiana)
    sys.exit(0)

# backup
import shutil, datetime
bak = sciezka + ".bak-fixdpms-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(sciezka, bak)
print(f"backup: {bak}")

with open(sciezka, "w", encoding="utf-8", errors="surrogateescape") as f:
    f.write(nowa)

# weryfikacja
with open(sciezka, encoding="utf-8", errors="surrogateescape") as f:
    sprawdzenie = f.read()
if "then(self.wakeupScreen.bind(self))" in sprawdzenie:
    print("OK: armowanie DPMS dodane")
    sys.exit(0)
else:
    print("BLAD: zapis nie przyniosl efektu", file=sys.stderr)
    sys.exit(1)
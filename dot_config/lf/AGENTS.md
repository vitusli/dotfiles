# lf config

Ziel: Das Verhalten von **Marta** (GUI-Dateimanager für macOS) so genau wie möglich im Terminal mit lf nachbilden. Neue Keybindings und Befehle sollen sich wie in Marta anfühlen.

## Referenz: Marta-Config

- Eigene Einstellungen: `~/Library/Application Support/org.yanex.marta/conf.marco`
- Standard-Config (alle Defaults): `/Applications/Marta.app/Contents/Resources/conf.marco`
- Favoriten: `~/Library/Application Support/org.yanex.marta/favorites.marco`

Bei Änderungen zuerst dort nachsehen, was Marta macht, und dann in lf nachbauen.

## Dateien

- `lfrc`: Keybindings und Befehle
- `preview.sh`: Vorschau (bat, Archive, PDF)
- `cleaner.sh`: Cleaner für die Vorschau

- `lfrc.windows`: Windows-Variante für die Nutzung über SSH (siehe unten)

Verwaltet mit chezmoi: Quelle ist `~/.local/share/chezmoi/dot_config/lf/`, nicht `~/.config/lf/` direkt bearbeiten. Danach `chezmoi apply ~/.config/lf`.

## Windows (`lfrc.windows`)

Der Hauptzweck: Wer per SSH auf einer Windows-Maschine ist, soll einen Dateimanager mit denselben Marta-Hotkeys haben.

- **Wird nicht von chezmoi deployt** (steht in `.chezmoiignore`). Die Datei wird manuell per SSH nach `%APPDATA%\lf\lfrc` kopiert, z. B.:
  `scp dot_config/lf/lfrc.windows <user>@<host>:AppData/Roaming/lf/lfrc`
- lf auf Windows installieren: `scoop install lf`. Optional `scoop install neovim`, sonst öffnet Enter Dateien im Pager.
- Shell ist Windows PowerShell 5.1 (`powershell`), weil `pwsh` nicht überall installiert ist. Shell-Befehle immer **einzeilig** schreiben, mehrzeilige `cmd`-Blöcke funktionieren unter Windows nicht zuverlässig. Dateivariablen heißen `$env:f`, `$env:fx`, `$env:id`.
- Keybindings so weit wie möglich identisch zur macOS-`lfrc` halten. Wenn sich dort eine Taste ändert, hier mitziehen.
- Unterschiede zu macOS, weil über SSH keine GUI da ist:
  - Space schaltet die Vorschau-Spalte um (kein Quick Look).
  - Ctrl+X löscht **endgültig** mit lfs eigener Rückfrage. Über SSH gibt es keinen Papierkorb (getestet: Datei war weg, nicht im Papierkorb).
  - `y`/`Y` kopieren per OSC 52 in die Zwischenablage des lokalen Rechners (kommt durch ConPTY/OpenSSH durch).
  - Kein Reveal in Explorer, kein VS Code, kein Open-with.
  - `f`/`n`: lf hängt den eingegebenen Namen an den PowerShell-Befehl an. Namen mit Leerzeichen deshalb in Anführungszeichen setzen.

## Bewusste Abweichungen von Marta

- `x`/`c` schneiden aus bzw. kopieren, eingefügt wird mit `p`. In Marta gehen sie direkt ins andere Panel, lf hat nur eins.
- Cmd-Shortcuts aus Marta (Desktop, Documents, Downloads, Terminal) kommen im Terminal nicht an. Downloads liegt deshalb auf `W`.
- Lesezeichen-Sprünge (`P`, `A`, `D`, `C`, `W`) starten danach den Filter.
- Enter öffnet Dateien in nvim, `l` öffnet sie mit der Standard-App (wie Marta).

## Fallstricke

- `map X cmd1; cmd2` ohne führendes `:` beendet das `map` am `;`, und `cmd2` läuft beim Start von lf. Mehrere Befehle immer als `map X :cmd1; cmd2`.
- Direkt nach dem Start (ca. 1–2 s) sind `$f`/`$fx` leer. `/usr/bin/trash ""` verschiebt dann das aktuelle Verzeichnis in den Papierkorb, deshalb prüft `cmd trash` auf leeres `$fx`.
- Prompts in `%`-Befehlen (shell-pipe) erscheinen erst nach der Eingabe. Für Eingaben `push :befehl<space>` nutzen, für Ja/Nein-Fragen `$`-Befehle.

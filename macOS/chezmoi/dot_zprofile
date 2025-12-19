######################################################################
# ~/.zprofile (wird nur bei Login-Shells ausgeführt)
# Zweck: Grundlegende Pfad-/Environment-Initialisierung. Interaktive
# Einstellungen, Aliases usw. gehören in ~/.zshrc.
######################################################################

## 1. Systempfade
# macOS ruft bereits in /etc/zprofile automatisch
#   /usr/libexec/path_helper -s
# auf. Falls Du jemals eine minimalistische Shell startest, die das
# NICHT macht, kannst Du die folgende Zeile entkommentieren:
# eval "$(/usr/libexec/path_helper -s)"

## 2. Homebrew Umgebung
# Stellt PATH, MANPATH etc. ein. Setzt /opt/homebrew/bin ganz nach vorne.
eval "$(/opt/homebrew/bin/brew shellenv)"

## 3. Benutzerbinärdateien (pipx, eigene Skripte)
# Idempotent hinzufügen, nur wenn noch nicht vorhanden.
case ":$PATH:" in
	*":$HOME/.local/bin:"*) ;;
	*) PATH="$HOME/.local/bin:$PATH" ;;
esac

## 4. TeX / BasicTeX (falls installiert)
# Einheitlicher Symlink-Pfad von MacTeX/BasicTeX: /Library/TeX/texbin
if [ -d /Library/TeX/texbin ]; then
	case ":$PATH:" in
		*":/Library/TeX/texbin:"*) ;;
		*) PATH="/Library/TeX/texbin:$PATH" ;;
	esac
fi

export PATH

######################################################################
# Hinweise:
# - Keine wiederholten "export PATH=$PATH:..." Anhänge, um Duplikate
#   und wachsende Länge zu vermeiden.
# - Reihenfolge wichtig: Eigene Tools (pipx) vor System, aber nach
#   Homebrew, damit Homebrew-Versionen bevorzugt werden.
# - Anpassungen für interaktive Nutzung (Prompt, Completion etc.) in
#   ~/.zshrc, nicht hier.
######################################################################


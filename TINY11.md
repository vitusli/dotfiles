# Tiny11Builder vs. Windows.ps1 – Vergleich und Analyse

## Übersicht

Diese Dokumentation vergleicht den **Tiny11Builder** (Offline-ISO-Ansatz) mit einem **Top-Down-Ansatz** wie dem `windows.ps1` Bootstrap-Skript.

---

## Was ist Tiny11Builder?

Das `tiny11maker.ps1` aus [ntdevlabs/tiny11builder](https://github.com/ntdevlabs/tiny11builder) ist ein **Offline-Image-Manipulation-Tool**, das:

1. **Windows ISO mountet** und das WIM-Image direkt bearbeitet
2. **~50+ Apps vollständig entfernt** (Clipchamp, Bing-Apps, Teams, Copilot, Xbox, OneDrive, Edge, etc.)
3. **Registry-Einträge im Offline-Image** setzt (Telemetrie deaktivieren, Sponsored Apps blocken, OOBE-Bypass)
4. **Scheduled Tasks löscht** (Telemetrie, CEIP, Error Reporting)
5. **Hardware-Requirement-Checks umgeht** (TPM, SecureBoot, etc.)
6. **Ein neues, sauberes ISO erstellt**

---

## Top-Down-Ansatz (Windows.ps1)

Ein Bootstrap-Skript wie `windows.ps1` arbeitet auf einem **bereits installierten Windows-System** und:

- Installiert gewünschte Pakete (z.B. via Scoop)
- Klont Repositories
- Richtet Entwicklungsumgebung ein
- Kann Apps deinstallieren und Registry-Tweaks anwenden

---

## Direkter Vergleich

| Aspekt | Tiny11Builder | Windows.ps1 (Top-Down) |
|--------|---------------|------------------------|
| **Entfernung von Bloatware** | ✅ Komplett, vor der Installation | ⚠️ Begrenzt, läuft auf laufendem System |
| **Edge entfernen** | ✅ Vollständig möglich | ❌ Sehr schwer auf laufendem System |
| **OneDrive entfernen** | ✅ Komplett | ⚠️ Möglich, aber Reste bleiben |
| **Registry-Tweaks** | ✅ Direkt im Image | ✅ Auch möglich |
| **Reproduzierbarkeit** | ✅ Gleiches Image jedes Mal | ⚠️ Abhängig vom Windows-Zustand |
| **Zeitaufwand** | Einmal Image bauen → immer nutzen | Bei jeder Neuinstallation ausführen |
| **Performance-Gewinn** | 🔥 Maximal (weniger läuft von Anfang an) | 🔶 Gut, aber Reste möglich |

---

## Warum der Top-Down-Ansatz Grenzen hat

1. **Manche Apps lassen sich auf einem laufenden System nicht entfernen** (Edge, einige System-Apps)
2. **Scheduled Tasks und Telemetrie-Dienste sind schon gelaufen** bevor das Skript startet
3. **Reste bleiben** – Registry-Einträge, leere Ordner, etc.

---

## Vorteile des Top-Down-Ansatzes

1. **Flexibilität:** Arbeitet mit existierendem, installiertem Windows-System
2. **Schnelles Testing:** Änderungen sind sofort sichtbar
3. **Keine komplizierte ISO-Erstellung:** Kein ADK oder ISO-Montagetools nötig

---

## Empfehlung: Kombination beider Ansätze

**Für maximale Performance und minimale Bloatware:**

1. **Erstelle ein Tiny11-Image** als Basis für alle Windows-Installationen
2. **Nutze windows.ps1** für den Post-Install-Setup (Scoop, Repos, Tools, zusätzliche Tweaks)

---

## Code-Snippets für Windows.ps1 Erweiterung

### App-Entfernung (wie in Tiny11)

```powershell
$appsToRemove = @(
    "Microsoft.BingNews",
    "Microsoft.BingWeather", 
    "Microsoft.GamingApp",
    "Microsoft.GetHelp",
    "Microsoft.Getstarted",
    "Microsoft.MicrosoftSolitaireCollection",
    "Microsoft.People",
    "Microsoft.WindowsFeedbackHub",
    "Microsoft.WindowsMaps",
    "Microsoft.ZuneMusic",
    "Microsoft.ZuneVideo",
    "Microsoft.YourPhone",
    "Microsoft.Todos",
    "Clipchamp.Clipchamp",
    "Microsoft.OutlookForWindows",
    "MicrosoftTeams",
    "Microsoft.549981C3F5F10"  # Cortana
)

foreach ($app in $appsToRemove) {
    Get-AppxPackage -Name $app -AllUsers | Remove-AppxPackage -AllUsers -ErrorAction SilentlyContinue
    Get-AppxProvisionedPackage -Online | Where-Object {$_.DisplayName -eq $app} | Remove-AppxProvisionedPackage -Online -ErrorAction SilentlyContinue
}
```

### Telemetrie deaktivieren

```powershell
# Advertising ID deaktivieren
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo" -Name "Enabled" -Value 0 -Type DWord -Force

# Tailored Experiences deaktivieren
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy" -Name "TailoredExperiencesWithDiagnosticDataEnabled" -Value 0 -Type DWord -Force

# Telemetrie auf Minimum
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" -Force | Out-Null
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" -Name "AllowTelemetry" -Value 0 -Type DWord -Force
```

### Sponsored Apps deaktivieren

```powershell
$cdmPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
Set-ItemProperty -Path $cdmPath -Name "ContentDeliveryAllowed" -Value 0 -Type DWord -Force
Set-ItemProperty -Path $cdmPath -Name "OemPreInstalledAppsEnabled" -Value 0 -Type DWord -Force
Set-ItemProperty -Path $cdmPath -Name "PreInstalledAppsEnabled" -Value 0 -Type DWord -Force
Set-ItemProperty -Path $cdmPath -Name "SilentInstalledAppsEnabled" -Value 0 -Type DWord -Force
Set-ItemProperty -Path $cdmPath -Name "SoftLandingEnabled" -Value 0 -Type DWord -Force
Set-ItemProperty -Path $cdmPath -Name "SubscribedContentEnabled" -Value 0 -Type DWord -Force
```

---

## Fazit

- **Tiny11 = Sauberer Start** (alles entfernt bevor es überhaupt installiert wird)
- **Windows.ps1 = Nachbesserung und Setup** (installiert Tools, wendet Tweaks an)

Die Kombination aus beidem ist der optimale Weg für ein schlankes, performantes Windows ohne Bloatware.

---

*Erstellt am: 2025-12-29*

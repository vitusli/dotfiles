# Diskussionsgrundlage
- Exakte Darstellung der realen Welt im digitalen Raum
	- Wenn die Kunden und Mitarbeitenden etwas wissen wollen, kann im 3D-Modell alles optimal dargestellt werden
		- Perspektive 
		- Licht
		- Farbe
- Änderungen an der ganzen Szene sind sehr schnell gemacht
- Der digitale Zwilling ist damit nicht nur Abbild sondern auch Vorbild für die Realität 
- Der digitale Zwilling für Wandelbots ist mit dem gleichen Skript steuerbar wie der reale Roboter
	- Allerdings ist ein digitaler Roboter günstiger im Betrieb und der Wartung
# Echzeit-Anwendung
- Beim digitalen Zwilling muss, da es sich um eine Echtzeit-Anwendung handelt, auf Performance geachtet werden ([[NVIDIA 2023]]) ([[Sasikumar A. et al 2023]]) 
	- Es ist ein niedrige Polygon-Anzahl (Polycount) anzustreben
		- Der Polycount ist von der Anwendung abhängig
		- Das beste erzielbare Ergebnis für Omniverse liegt bei 50.000 Polygonen
		- Für das Web ist ein sehr guter Polycount 5000 Polygone, bei hohem Verlust der Außenkontur - Zylinder haben an den Konturen sichtbare Kanten, während überwölbte Flächen weiterhin hohe Qualität aufweisen, da eine Normal Map (Referenz) auf diese projiziert wird
	- Trotz niedrigem Polycount kann eine sehr hohe Oberflächen-Darstellung erreicht werden
	- Texturen sind so klein wie nötig zu halten (Material Best Practise)
	

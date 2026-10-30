Bron 1: Funda-aanbod (gegeven), funda_M_2026-10-03_samen_met_buurten_data_2026-10-03.xlsx, 6.864 listings, peildatum 3 okt 2026.
Bewerking: prijs en woonoppervlak naar numeriek (17 prijzen en 161 oppervlaktes onbekend -> NaN), prijs per m² = Vraagprijs / Wonen, filter op coördinaten binnen Amsterdam.

Bron 2: tram- en metrohaltes, OpenStreetMap via Overpass API, opgehaald met fetch_stops.py op [datum], [N] haltes.

Koppeling: geen gemeenschappelijke sleutel; ruimtelijke koppeling via coördinaten: per woning de dichtstbijzijnde halte (KD-tree) en afstand tot Amsterdam Centraal (haversine). Rijen na koppeling: [N uit de app].

Wat misging: eerste Overpass-query (railway=tram) leverde geen haltes op maar baanpunten/alleen metro-ingangen; aangepast naar railway=tram_stop en station=subway.

Beperkingen: vraagprijzen, één snapshot, hemelsbrede afstand.
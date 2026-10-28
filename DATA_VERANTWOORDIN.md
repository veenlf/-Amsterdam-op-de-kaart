Bron 1: Funda (Aanbod)

Bestand: funda_M_2026-10-03_samen_met_buurten_data_2026-10-03.xlsx

Herkomst: Verstrekt door de docent. Bevat 6.864 listings.

Bewerking: Rijen zonder straatnaam of coördinaten verwijderd. Prijzen ("Onbekend") omgezet naar NaN. Prijs per m² berekend (Vraagprijs / Wonen).

Bron 2: Kadaster (Verkopen)

Bestand: clean_kadaster_data.csv

Herkomst: Verstrekt door de docent.

Bewerking: Tekst in de Koopsom kolom (zoals "Kadastralegrootte...") verwijderd via Regex. Rijen met ongeldige GPS-coördinaten (Latitude buiten 52.2-52.5) verwijderd.

Samenvoeging (Merge)

De twee datasets zijn samengevoegd op basis van een zelfgemaakte string-sleutel: straatnaam|huisnummer.

Om suffixen (zoals -A, -B) te negeren, is er een Regex gebruikt om alleen het basisnummer te pakken.

Resultaat: [Vul hier in hoeveel matches je had op basis van je echte Kadaster-data].
Bron 1: Funda (Aanbod)

Bestand: funda_M_2026-10-03_samen_met_buurten_data_2026-10-03.xlsx

Herkomst: Verstrekt door de docent. Bevat 6.864 listings.

Bewerking: Rijen zonder straatnaam of coördinaten verwijderd. Prijzen ("Onbekend") omgezet naar NaN. Prijs per m² berekend (Vraagprijs / Wonen).

Bron 2: CBS Woningvoorraad

Endpoint: https://opendata.cbs.nl/ODataApi/OData/83704NED

Fetched via requests.get() in fetch_cbs.py on [date].

Filtered to Regio = Amsterdam, years 2012–2026.

Joined to Funda at the municipality level (Amsterdam), producing N rows for statistical analysis.

Limitation: CBS data is municipality-level, not buurt-level, so spatial correlation with Funda buurten is approximate.
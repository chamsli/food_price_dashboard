import csv
from collections import Counter
from services import data_service as ds

path = ds.DATA_FILE
delim = ds.detect_delimiter(path)
encoding = ds.detect_encoding(path)
print("Codificación detectada:", encoding, "| separador:", repr(delim))
with open(path, encoding=encoding, newline="") as f:
    raw = list(csv.DictReader(f, delimiter=delim))

print("Filas en el CSV original:", len(raw))
print("Columnas:", list(raw[0].keys()))
print("Series (Item) distintas:", Counter(r["Item"] for r in raw).most_common(5))
print("Códigos de mes:", sorted({r["Months Code"] for r in raw})[:15])
print("Años:", min(r["Year"] for r in raw), "-", max(r["Year"] for r in raw))
print("Valores distintos en 'Value':", len({r["Value"] for r in raw}))

clean = ds.load_clean_data()
print("\nFilas tras la limpieza:", len(clean), "| países:", len(ds.get_countries()))

country = "Spain" if "Spain" in ds.get_countries() else ds.get_countries()[0]
print(f"\nResumen anual de {country} :")
for r in ds.country_rows(country):
    print(f"  {r['year']}: índice medio {r['avg_index']:>8}  inflación {r['inflation']}  meses {r['months']}")

print("\nMarcas de fiabilidad (Flag) de la serie del índice:")
item = ds.get_item_name()
flags = Counter((r["Flag"], r["Flag Description"]) for r in raw if r["Item"] == item)
for (flag, description), n in flags.most_common():
    print(f"  {flag!r:6} {description}: {n} filas")
no_official = [c for c in ds.get_countries() if not any(r["official"] for r in clean if r["country"] == c)]
print("Países sin ningún valor oficial:", no_official or "ninguno")

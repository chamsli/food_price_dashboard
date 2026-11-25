"""Lectura, limpieza y consultas sobre el CSV de FAOSTAT."""
import csv
import os
from statistics import median

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "food_prices.csv")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
SORTABLE = ("country", "year", "avg_index", "inflation", "since_start", "months", "official_pct")

_cache = None    # registros mensuales limpios
_summary = None  # resumen anual por país


# ---------------------------------------------------------------- carga y limpieza
def detect_encoding(path):
    """Prueba UTF-8 y, si falla, la codificación de Windows/Excel (cp1252)."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, encoding=encoding) as f:
                f.read()
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detect_delimiter(path):
    """Los CSV pueden venir separados por comas, punto y coma o tabuladores."""
    with open(path, encoding=detect_encoding(path)) as f:
        header = f.readline()
    return max((",", ";", "\t"), key=header.count)


def load_clean_data():
    """Lee el CSV y devuelve una lista de registros mensuales limpios.
    Limpieza: 1) nos quedamos solo con las columnas útiles, 2) convertimos
    año/mes/valor a números, 3) descartamos filas vacías o inválidas,
    4) marcamos si el valor es oficial (flag A) o imputado/estimado,
    5) eliminamos duplicados.
    """
    global _cache
    if _cache is not None:
        return _cache

    rows, seen = [], set()
    with open(DATA_FILE, encoding=detect_encoding(DATA_FILE), newline="") as f:
        reader = csv.DictReader(f, delimiter=detect_delimiter(DATA_FILE))
        for raw in reader:
            try:
                country = raw["Area"].strip()
                year = int(raw["Year"])
                month = int(raw["Months Code"]) - 7000  # 7001 -> 1 (enero)
                value = float(raw["Value"])
            except (KeyError, ValueError, TypeError, AttributeError):
                continue  # valor ausente o inválido: se descarta la fila
            if not country or not 1 <= month <= 12:
                continue
            key = (country, raw.get("Item", ""), year, month)
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "country": country,
                "item": raw.get("Item", "").strip(),
                "year": year,
                "month": month,
                "value": round(value, 2),
                "official": raw.get("Flag", "").strip() == "A",
            })
    rows = _keep_main_item(rows)
    _cache = rows
    return rows


def _keep_main_item(rows):
    """Si el CSV mezcla varias series (p. ej. índice e inflación), nos quedamos
    con una sola para no mezclar unidades: la del índice de alimentos."""
    counts = {}
    for r in rows:
        counts[r["item"]] = counts.get(r["item"], 0) + 1
    if len(counts) <= 1:
        return rows
    preferred = [i for i in counts if "food" in i.lower() and "indices" in i.lower()]
    main = max(preferred or counts, key=lambda i: counts[i])
    return [r for r in rows if r["item"] == main]


def get_item_name():
    rows = load_clean_data()
    return rows[0]["item"] if rows else ""


def get_base_label():
    """Etiqueta del índice, p. ej. 'Índice de precios (2015 = 100)'."""
    item = get_item_name()
    if "(" in item and ")" in item:
        return "Índice de precios de alimentos " + item[item.index("("):item.index(")") + 1]
    return "Índice de precios de alimentos"


def get_countries():
    return sorted({r["country"] for r in load_clean_data()})


def get_years():
    return sorted({r["year"] for r in load_clean_data()})


# ---------------------------------------------------------------- resumen anual
def yearly_summary():
    """Un registro por país y año: índice medio, inflación, subida acumulada."""
    global _summary
    if _summary is not None:
        return _summary

    groups = {}
    for r in load_clean_data():
        groups.setdefault((r["country"], r["year"]), []).append(r)

    summary = {}
    for (country, year), items in groups.items():
        avg = sum(i["value"] for i in items) / len(items)
        official = 100 * sum(i["official"] for i in items) / len(items)
        summary[(country, year)] = {
            "country": country, "year": year, "avg_index": round(avg, 2),
            "months": len(items), "official_pct": round(official),
            "inflation": None, "since_start": None,
        }
    # inflación respecto al año anterior y subida acumulada desde el primer año
    for country in {c for c, _ in summary}:
        years = sorted(y for c, y in summary if c == country)
        first = summary[(country, years[0])]["avg_index"]
        for y in years:
            cur = summary[(country, y)]
            cur["since_start"] = round((cur["avg_index"] / first - 1) * 100, 1)
            prev = summary.get((country, y - 1))
            if prev:
                cur["inflation"] = round((cur["avg_index"] / prev["avg_index"] - 1) * 100, 1)
    _summary = list(summary.values())
    return _summary


# ---------------------------------------------------------------- consultas
def query_table(country="", year_from=None, year_to=None, sort_by="country", order="asc"):
    """Filas anuales filtradas y ordenadas para la tabla del panel."""
    rows = yearly_summary()
    if country:
        rows = [r for r in rows if r["country"] == country]
    if year_from:
        rows = [r for r in rows if r["year"] >= year_from]
    if year_to:
        rows = [r for r in rows if r["year"] <= year_to]
    if sort_by not in SORTABLE:
        sort_by = "country"
    # los valores vacíos (p. ej. inflación del primer año) van siempre al final
    with_val = [r for r in rows if r[sort_by] is not None]
    without = [r for r in rows if r[sort_by] is None]
    with_val.sort(key=lambda r: (r[sort_by], r["country"], r["year"]), reverse=(order == "desc"))
    return with_val + without


def paginate(rows, page, per_page=20):
    """Devuelve (filas de la página, página actual, total de páginas)."""
    pages = max(1, -(-len(rows) // per_page))
    page = min(max(page or 1, 1), pages)
    start = (page - 1) * per_page
    return rows[start:start + per_page], page, pages


def series_for_country(country):
    """(años, índice medio anual) de un país, listo para graficar."""
    rows = sorted((r for r in yearly_summary() if r["country"] == country), key=lambda r: r["year"])
    return [r["year"] for r in rows], [r["avg_index"] for r in rows]


def monthly_for_country(country):
    return sorted((r for r in load_clean_data() if r["country"] == country),
                  key=lambda r: (r["year"], r["month"]))


def country_rows(country):
    return sorted((r for r in yearly_summary() if r["country"] == country), key=lambda r: r["year"])


def month_detail(country, year):
    """Detalle mes a mes de un país y año.

    Devuelve (meses, resumen). Cada mes incluye la variación respecto al mes
    anterior (enero se compara con diciembre del año previo si existe).
    Devuelve (None, None) si no hay datos de ese país y año."""
    values = {(r["year"], r["month"]): r for r in monthly_for_country(country)}
    months = []
    for month in range(1, 13):
        r = values.get((year, month))
        if not r:
            continue
        prev = values.get((year, month - 1)) if month > 1 else values.get((year - 1, 12))
        change = round((r["value"] / prev["value"] - 1) * 100, 2) if prev else None
        months.append({"month": month, "name": MESES[month - 1].capitalize(),
                       "value": r["value"], "change": change, "official": r["official"]})
    if not months:
        return None, None

    with_change = [m for m in months if m["change"] is not None]
    summary = {
        "first": months[0], "last": months[-1],
        "total_change": round((months[-1]["value"] / months[0]["value"] - 1) * 100, 1),
        "highest": max(months, key=lambda m: m["value"]),
        "lowest": min(months, key=lambda m: m["value"]),
        "biggest_rise": max(with_change, key=lambda m: m["change"]) if with_change else None,
        "biggest_drop": min(with_change, key=lambda m: m["change"]) if with_change else None,
        "official": sum(m["official"] for m in months),
        "count": len(months),
    }
    years = sorted({y for (y, _) in values})
    summary["prev_year"] = year - 1 if year - 1 in years else None
    summary["next_year"] = year + 1 if year + 1 in years else None
    return months, summary


def ranking_for_year(year, top=10):
    """Los países con mayor inflación alimentaria en un año."""
    rows = [r for r in yearly_summary() if r["year"] == year and r["inflation"] is not None]
    return sorted(rows, key=lambda r: r["inflation"], reverse=True)[:top]


def median_inflation_by_year():
    """(años, inflación mediana de todos los países). Usamos la mediana porque
    unos pocos países con hiperinflación distorsionarían la media."""
    by_year = {}
    for r in yearly_summary():
        if r["inflation"] is not None:
            by_year.setdefault(r["year"], []).append(r["inflation"])
    years = sorted(by_year)
    return years, [round(median(by_year[y]), 1) for y in years]


def default_year():
    """Último año con datos de inflación en al menos la mitad de los países."""
    counts = {}
    for r in yearly_summary():
        if r["inflation"] is not None:
            counts[r["year"]] = counts.get(r["year"], 0) + 1
    if not counts:
        return None
    limit = max(counts.values()) / 2
    return max(y for y, n in counts.items() if n >= limit)


def default_countries(n=4):
    preferred = ["Spain", "France", "Germany", "United States of America", "Italy"]
    available = get_countries()
    chosen = [c for c in preferred if c in available][:n]
    return chosen or available[:n]


def get_insights():
    """Datos clave que se muestran en el panel."""
    rows = [r for r in yearly_summary() if r["inflation"] is not None]
    if not rows:
        return {}
    year = default_year()
    latest = [r for r in rows if r["year"] == year]
    top_cumulative = max((r for r in yearly_summary() if r["year"] == year),
                         key=lambda r: r["since_start"], default=None)
    return {
        "countries": len(get_countries()),
        "years": f"{get_years()[0]}–{get_years()[-1]}",
        "records": len(load_clean_data()),
        "worst": max(rows, key=lambda r: r["inflation"]),
        "year": year,
        "median_latest": round(median(r["inflation"] for r in latest), 1) if latest else None,
        "top_cumulative": top_cumulative,
    }

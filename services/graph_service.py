
import base64
from io import BytesIO

from matplotlib.figure import Figure

INK, TEAL, RED, GREEN, GRID = "#0F2742", "#1D4E89", "#C8372D", "#2A9D8F", "#DDE3EA"
PALETTE = ["#1D4E89", "#C8372D", "#E0A030", "#2A9D8F", "#6C5B9E", "#6B7C8C"]


def _prepare(figsize=(9, 4.6)):
    figure = Figure(figsize=figsize)
    axes = figure.subplots()
    axes.set_facecolor("white")
    for side in ("top", "right"):
        axes.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axes.spines[side].set_color("#9AA8B0")
    axes.tick_params(colors=INK, labelsize=9)
    axes.grid(axis="y", color=GRID, linewidth=0.8)
    axes.set_axisbelow(True)
    return figure, axes


def _to_base64(figure):
    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=110, bbox_inches="tight")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def line_chart(series, base_label):
    """Compara el índice anual de varios países. series: {país: (años, valores)}"""
    figure, axes = _prepare()
    for i, (country, (years, values)) in enumerate(series.items()):
        axes.plot(years, values, marker="o", markersize=4, linewidth=2,
                  color=PALETTE[i % len(PALETTE)], label=country)
    axes.axhline(100, color="#9AA8B0", linestyle="--", linewidth=1)
    axes.set_ylabel(base_label, color=INK)
    axes.set_xlabel("Año", color=INK)
    axes.xaxis.get_major_locator().set_params(integer=True)
    if series:
        axes.legend(frameon=False, fontsize=9)
    return _to_base64(figure)


def ranking_chart(rows, year):
    """Barras horizontales: países con mayor inflación alimentaria en un año."""
    figure, axes = _prepare()
    axes.grid(axis="x", color=GRID, linewidth=0.8)
    axes.grid(axis="y", visible=False)
    rows = list(reversed(rows))  # el mayor arriba
    names = [r["country"] for r in rows]
    values = [r["inflation"] for r in rows]
    bars = axes.barh(names, values, color=[RED if v >= 0 else GREEN for v in values])
    for bar, value in zip(bars, values):
        axes.text(bar.get_width(), bar.get_y() + bar.get_height() / 2, f" {value:.1f}%",
                  va="center", fontsize=9, color=INK)
    axes.set_xlabel(f"Inflación de los alimentos en {year} (%)", color=INK)
    axes.margins(x=0.12)
    return _to_base64(figure)


def median_chart(years, values):
    """Barras: inflación mediana de todos los países, año a año."""
    figure, axes = _prepare()
    axes.bar(years, values, color=[RED if v == max(values) else TEAL for v in values])
    axes.axhline(0, color=INK, linewidth=0.8)
    axes.set_ylabel("Inflación mediana (%)", color=INK)
    axes.set_xlabel("Año", color=INK)
    axes.xaxis.get_major_locator().set_params(integer=True)
    return _to_base64(figure)


def monthly_chart(country, monthly, base_label):
    """Evolución mensual de un país; diferencia valores oficiales e imputados."""
    figure, axes = _prepare()
    xs = [r["year"] + (r["month"] - 1) / 12 for r in monthly]
    ys = [r["value"] for r in monthly]
    axes.plot(xs, ys, color=TEAL, linewidth=1.8)
    axes.scatter([x for x, r in zip(xs, monthly) if not r["official"]],
                 [y for y, r in zip(ys, monthly) if not r["official"]],
                 s=14, color="#E0A030", zorder=3, label="Valor imputado/estimado")
    axes.axhline(100, color="#9AA8B0", linestyle="--", linewidth=1)
    axes.set_ylabel(base_label, color=INK)
    axes.set_xlabel("Año", color=INK)
    axes.set_title(country, loc="left", color=INK, fontsize=11)
    axes.legend(frameon=False, fontsize=9)
    return _to_base64(figure)


def year_index_chart(months, base_label):
    """Índice mes a mes dentro de un año; amarillo = valor estimado."""
    figure, axes = _prepare((7, 4))
    names = [m["name"][:3] for m in months]
    values = [m["value"] for m in months]
    axes.plot(names, values, color=TEAL, linewidth=2)
    axes.scatter(names, values, s=40, zorder=3,
                 color=[TEAL if m["official"] else "#E0A030" for m in months])
    low, high = min(values), max(values)
    margin = max((high - low) * 0.25, 0.5)
    axes.set_ylim(low - margin, high + margin)
    axes.set_ylabel(base_label, color=INK)
    return _to_base64(figure)


def year_change_chart(months):
    """Variación mensual (%): rojo si los precios suben, verde si bajan."""
    figure, axes = _prepare((7, 4))
    data = [m for m in months if m["change"] is not None]
    names = [m["name"][:3] for m in data]
    changes = [m["change"] for m in data]
    axes.bar(names, changes, color=[RED if c >= 0 else GREEN for c in changes])
    axes.axhline(0, color=INK, linewidth=0.8)
    axes.set_ylabel("Variación respecto al mes anterior (%)", color=INK)
    return _to_base64(figure)

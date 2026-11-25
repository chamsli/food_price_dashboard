from flask import Flask, abort, render_template, request

from services import data_service as ds
from services import graph_service as gs

app = Flask(__name__)


@app.route("/")
def dashboard():
    country = request.args.get("country", "")
    year_from = request.args.get("year_from", type=int)
    year_to = request.args.get("year_to", type=int)
    sort_by = request.args.get("sort", "country")
    order = "desc" if request.args.get("order") == "desc" else "asc"
    detail = request.args.get("detail") == "full"
    page = request.args.get("page", 1, type=int)

    rows = ds.query_table(country, year_from, year_to, sort_by, order)
    page_rows, page, pages = ds.paginate(rows, page)
    filters = {"country": country, "year_from": year_from, "year_to": year_to,
               "detail": "full" if detail else None}
    return render_template(
        "dashboard.html",
        rows=page_rows, total=len(rows), page=page, pages=pages,
        countries=ds.get_countries(), years=ds.get_years(),
        filters=filters, sort_by=sort_by, order=order, detail=detail,
        insights=ds.get_insights(), base_label=ds.get_base_label(),
    )


@app.route("/graficas")
def graficas():
    chosen = [c for c in request.args.getlist("countries") if c in ds.get_countries()]
    too_many = len(chosen) > 6
    countries = chosen[:6] or ds.default_countries()
    year = request.args.get("year", type=int)
    if year not in ds.get_years():
        year = ds.default_year()

    ranking = ds.ranking_for_year(year)
    median_years, median_values = ds.median_inflation_by_year()
    peak_year = median_years[median_values.index(max(median_values))] if median_values else None
    return render_template(
        "graficas.html",
        all_countries=ds.get_countries(), selected=countries, too_many=too_many,
        years=ds.get_years(), year=year, ranking=ranking, peak_year=peak_year,
        peak_value=max(median_values) if median_values else None,
        line_img=gs.line_chart({c: ds.series_for_country(c) for c in countries}, ds.get_base_label()),
        ranking_img=gs.ranking_chart(ranking, year),
        median_img=gs.median_chart(median_years, median_values),
    )


@app.route("/pais/<path:country>")
def pais(country):
    if country not in ds.get_countries():
        abort(404)
    rows = ds.country_rows(country)
    return render_template(
        "pais.html", country=country, rows=rows, meses=ds.MESES,
        chart=gs.monthly_chart(country, ds.monthly_for_country(country), ds.get_base_label()),
        base_label=ds.get_base_label(),
    )


@app.route("/detalle/<int:year>/<path:country>")
def detalle(year, country):
    months, summary = ds.month_detail(country, year)
    if months is None:
        abort(404)
    return render_template(
        "detalle.html", country=country, year=year, months=months, summary=summary,
        index_img=gs.year_index_chart(months, ds.get_base_label()),
        change_img=gs.year_change_chart(months), base_label=ds.get_base_label(),
    )


@app.errorhandler(404)
def not_found(_):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True)

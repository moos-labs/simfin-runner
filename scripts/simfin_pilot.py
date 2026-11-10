#!/usr/bin/env python3
"""SimFin pilot.

With SIMFIN_API_KEY set (workflow injects it from the org secret):
configures simfin via sf.set_api_key, loads the US companies dataset and
the annual income statements, extracts the AAPL slice, and writes
results/summary.json plus results/companies_us.csv and
results/aapl_income.csv. The key value is never printed or recorded.

Without the key: runs the documented keyless probe instead - one
load_companies call whose 401 error is recorded verbatim in
results/summary.json and results/key_requirement.md, exiting 0 (the
keyless failure is the finding, as in scripts/simfin_probe.py).
"""
import json
import os
import traceback

os.makedirs("results", exist_ok=True)

summary = {"key_present": bool(os.environ.get("SIMFIN_API_KEY"))}


def write_summary():
    with open("results/summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)


try:
    import simfin as sf
    summary["simfin_version"] = getattr(sf, "__version__", "UNKNOWN")
except Exception as e:
    summary["import_error"] = f"{type(e).__name__}: {e}"
    write_summary()
    raise

sf.set_data_dir("simfin_data/")

if not summary["key_present"]:
    # ---- Keyless path: documented 401, exit 0 ----
    try:
        sf.load_companies(market="us")
        summary["keyless_call"] = "succeeded (unexpected)"
    except Exception as e:
        summary["keyless_call"] = "failed"
        summary["keyless_error_type"] = type(e).__name__
        summary["keyless_error"] = str(e)
    with open("results/key_requirement.md", "w") as f:
        f.write("# SimFin - API key requirement\n\n")
        f.write("No SIMFIN_API_KEY was set for this run. Keyless data call result:\n\n")
        f.write(f"- error type: `{summary.get('keyless_error_type')}`\n")
        f.write(f"- error (verbatim): {summary.get('keyless_error')}\n\n")
        f.write("A personal free API key from simfin.com is required; store it as the "
                "SIMFIN_API_KEY secret and inject it into the Run-commands step.\n")
    write_summary()
    print("Keyless path: recorded result in results/summary.json")
    raise SystemExit(0)

# ---- Keyed path: real pilot ----
sf.set_api_key(os.environ["SIMFIN_API_KEY"])

try:
    companies = sf.load_companies(market="us")
    summary["companies_rows"] = int(companies.shape[0])
    summary["companies_columns"] = [str(c) for c in companies.columns]
    companies.to_csv("results/companies_us.csv")
    print(f"companies: {companies.shape[0]} rows")

    income = sf.load_income(variant="annual", market="us")
    summary["income_rows_total"] = int(income.shape[0])

    # AAPL slice: ticker may be the index or a column depending on version.
    inc = income.reset_index()
    ticker_col = next((c for c in inc.columns if str(c).lower() == "ticker"), None)
    if ticker_col is None:
        raise RuntimeError(f"no Ticker column/index in income data: {list(inc.columns)}")
    aapl = inc[inc[ticker_col] == "AAPL"].copy()
    summary["aapl_income_rows"] = int(aapl.shape[0])
    aapl.to_csv("results/aapl_income.csv", index=False)

    # Most recent fiscal years for AAPL: pick identifying + headline columns.
    date_col = next((c for c in aapl.columns if "report date" in str(c).lower()), None)
    fy_col = next((c for c in aapl.columns if str(c).lower() == "fiscal year"), None)
    if date_col is not None:
        aapl = aapl.sort_values(date_col)
    wanted = [c for c in ["Revenue", "Cost of Revenue", "Gross Profit",
                          "Operating Income (EBIT)", "Net Income",
                          "Selling, General & Administrative",
                          "Research & Development"] if c in aapl.columns]
    keep = [c for c in [ticker_col, fy_col, date_col] if c] + wanted
    recent = aapl[keep].tail(3)
    summary["aapl_income_recent"] = json.loads(recent.to_json(orient="records"))
    print(f"AAPL income rows: {aapl.shape[0]}")
    print(recent.to_string())
    summary["status"] = "ok"
except Exception as e:
    summary["status"] = "error"
    summary["error_type"] = type(e).__name__
    summary["error"] = str(e)
    summary["traceback"] = traceback.format_exc()
    write_summary()
    raise

write_summary()
print("Wrote results/summary.json, results/companies_us.csv, results/aapl_income.csv")

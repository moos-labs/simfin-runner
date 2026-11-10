# simfin-runner

Run [SimFin](https://github.com/SimFin/simfin) (`pip install simfin`) analysis on GitHub Actions, following the moos-labs runner pattern:

- Public repo under the **moos-labs** org, commands driven by the repo Actions variable `COMMANDS` (set via the variables API).
- `.github/workflows/run.yml` triggers on `workflow_dispatch` only, uses Python 3.11, installs `simfin` + `pandas`, runs `${{ vars.COMMANDS }}`, and always uploads `results/` as the `results` artifact.
- Scripts live in `scripts/`. The pilot is `scripts/simfin_probe.py`.

## Pilot: API-key requirement probe

`scripts/simfin_probe.py` prints the installed simfin version, attempts a keyless data call (`simfin.load_companies(market='us')`) with no API key, records the exact exception, inspects the installed library for any documented keyless/bulk-download route, and writes `results/key_requirement.md`. It exits 0 — the keyless failure is the finding.

## Key requirement (summary)

SimFin requires a personal API key for data downloads. Get a free key by signing up at **simfin.com**. To wire it here later: store it as the repo secret `SIMFIN_API_KEY` and call `simfin.set_api_key(os.environ['SIMFIN_API_KEY'])` before any data call. No account or key is created by this repo's probe.

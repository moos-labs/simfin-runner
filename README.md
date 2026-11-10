# simfin-runner

Run [SimFin](https://github.com/SimFin/simfin) (`pip install simfin`) analysis on GitHub Actions, following the moos-labs runner pattern:

- Public repo under the **moos-labs** org, commands driven by the repo Actions variable `COMMANDS` (set via the variables API).
- `.github/workflows/run.yml` triggers on `workflow_dispatch` only, uses Python 3.11, installs `simfin` + `pandas`, runs `${{ vars.COMMANDS }}`, and always uploads `results/` as the `results` artifact.
- Scripts live in `scripts/`. The pilot is `scripts/simfin_probe.py`.

## Pilot: API-key requirement probe

`scripts/simfin_probe.py` prints the installed simfin version (1.0.2), attempts a keyless data call (`simfin.load_companies(market='us')`) with no API key, records the exact exception, inspects the installed library for any documented keyless/bulk-download route, and writes `results/key_requirement.md`. It exits 0 — the keyless failure is the finding.

## Key requirement (summary)

SimFin requires a personal API key for data downloads — proven by the probe:

- No key set: `HTTPError: 401 Client Error: Unauthorized for url: https://prod.simfin.com/api/bulk-download/s3?dataset=companies&market=us`
- The library's documented fallback `simfin.load_api_key()` (default_key='free', `simfin/config.py:32`) was also tested: same 401. It does not grant access in practice.
- The bulk-download endpoint is the library's only download route, and it sends the key as an `Authorization: api-key <key>` header (`simfin/download.py:25-27`).

Get a free key by registering at **simfin.com** (`simfin/config.py:17`: "The user's API key obtained when registering on www.simfin.com"). To wire it here later: store it as the repo secret `SIMFIN_API_KEY` and call `simfin.set_api_key(os.environ['SIMFIN_API_KEY'])` before any data call. No account or key is created by this repo's probe.

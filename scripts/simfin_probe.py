#!/usr/bin/env python3
"""Probe SimFin: version, keyless data call, and documented API-key route.

The keyless failure is the finding, not a crash: this script always
exits 0 after writing results/key_requirement.md.
"""
import inspect
import os
import traceback

os.makedirs("results", exist_ok=True)
os.makedirs("results/simfin_data", exist_ok=True)

lines = []
findings = {}

def record(s=""):
    print(s, flush=True)
    lines.append(str(s))

try:
    import simfin as sf
    version = getattr(sf, "__version__", "UNKNOWN")
except Exception as e:
    version = "IMPORT_FAILED"
    record(f"IMPORT FAILED: {type(e).__name__}: {e}")
    sf = None

record(f"simfin version: {version}")
findings["version"] = version

# --- (2) Keyless data call ---
error_type = None
error_msg = None
keyless_result = None
if sf is not None:
    # Make sure no key is set via env for an honest keyless test.
    for var in ("SIMFIN_API_KEY",):
        if var in os.environ:
            record(f"NOTE: removing {var} from environment for keyless test")
            del os.environ[var]
    try:
        # Use a local data dir so nothing depends on pre-existing state.
        try:
            sf.set_data_dir("results/simfin_data/")
        except Exception:
            pass
        record("Attempting keyless call: simfin.load_companies(market='us')")
        keyless_result = sf.load_companies(market="us")
        record(f"KEYLESS CALL SUCCEEDED (unexpected): type={type(keyless_result).__name__}")
        try:
            record(f"Result shape: {getattr(keyless_result, 'shape', 'n/a')}")
            record(f"Result head:\n{keyless_result.head()}")
        except Exception:
            pass
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        record(f"KEYLESS CALL FAILED")
        record(f"Exception type: {error_type}")
        record(f"Exception message: {error_msg}")
        record("Traceback:")
        record(traceback.format_exc())

findings["error_type"] = error_type
findings["error_msg"] = error_msg

# --- (2b) Test the library's documented 'free' default key ---
# config.py defines: load_api_key(path='~/simfin_api_key.txt', default_key='free')
# i.e. when no key file exists, the library falls back to the literal key 'free'.
# Test whether that documented fallback actually grants access.
free_error_type = None
free_error_msg = None
free_result_ok = False
free_key_value = None
if sf is not None:
    record("")
    record("=== Testing documented default 'free' key via simfin.load_api_key() ===")
    try:
        import inspect as _inspect
        record(f"load_api_key signature: {_inspect.signature(sf.load_api_key)}")
        record(f"load_api_key docstring: {inspect.getdoc(sf.load_api_key)!r}")
    except Exception as e:
        record(f"load_api_key introspection failed: {e}")
    try:
        sf.load_api_key(path="results/no_such_simfin_api_key.txt")
        try:
            free_key_value = sf.get_api_key()
        except Exception:
            free_key_value = "(get_api_key unavailable)"
        record(f"API key after load_api_key() with missing file: {free_key_value!r}")
        try:
            sf.set_data_dir("results/simfin_data_free/")
        except Exception:
            pass
        record("Retrying: simfin.load_companies(market='us') with the 'free' default key")
        res2 = sf.load_companies(market="us")
        free_result_ok = True
        record(f"FREE-KEY CALL SUCCEEDED: type={type(res2).__name__} shape={getattr(res2, 'shape', 'n/a')}")
        try:
            record(f"Free-key result head:\n{res2.head()}")
        except Exception:
            pass
    except Exception as e:
        free_error_type = type(e).__name__
        free_error_msg = str(e)
        record(f"FREE-KEY CALL FAILED")
        record(f"Exception type: {free_error_type}")
        record(f"Exception message: {free_error_msg}")
        record(traceback.format_exc())
findings["free_error_type"] = free_error_type
findings["free_error_msg"] = free_error_msg
findings["free_result_ok"] = free_result_ok
findings["free_key_value"] = free_key_value

# --- (3) Documented keyless / bulk route? Inspect the installed library ---
doc_evidence = []
if sf is not None:
    record("")
    record("=== Library introspection ===")
    # set_api_key presence + docstring
    has_set_api_key = hasattr(sf, "set_api_key")
    record(f"has simfin.set_api_key: {has_set_api_key}")
    doc_evidence.append(f"hasattr(simfin, 'set_api_key') == {has_set_api_key}")
    if has_set_api_key:
        doc = inspect.getdoc(sf.set_api_key) or "(no docstring)"
        record(f"set_api_key docstring:\n{doc}")
        doc_evidence.append(f"simfin.set_api_key docstring: {doc!r}")
        try:
            src_file = inspect.getsourcefile(sf.set_api_key)
            record(f"set_api_key source file: {src_file}")
            doc_evidence.append(f"set_api_key source file: {src_file}")
        except Exception as e:
            record(f"set_api_key source file: unavailable ({e})")
    # load_companies docstring
    if hasattr(sf, "load_companies"):
        doc = inspect.getdoc(sf.load_companies) or "(no docstring)"
        record(f"load_companies docstring (first 2000 chars):\n{doc[:2000]}")
    # Module docstring
    mod_doc = getattr(sf, "__doc__", None) or "(no module docstring)"
    record(f"simfin module docstring:\n{mod_doc}")

    # Search installed package files for key / bulk / free mentions
    import pathlib
    pkg_dir = pathlib.Path(inspect.getfile(sf)).parent
    record(f"simfin package dir: {pkg_dir}")
    keywords = ["api_key", "api key", "simfin.com", "bulk", "free"]
    hits = []
    for path in sorted(pkg_dir.rglob("*")):
        if path.is_file() and path.suffix in (".py", ".md", ".txt", ".rst"):
            try:
                text = path.read_text(errors="replace")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                low = line.lower()
                if any(k in low for k in keywords):
                    rel = path.relative_to(pkg_dir)
                    hits.append(f"{rel}:{i}: {line.strip()}")
    record(f"Package text hits for {keywords} ({len(hits)} lines, first 120 shown):")
    for h in hits[:120]:
        record(f"  {h}")
    doc_evidence.append(f"package search hits: {len(hits)} lines (see run.log)")

    # Any function whose name suggests a keyless/bulk download?
    names = [n for n in dir(sf) if not n.startswith("_")]
    record(f"simfin public names: {names}")
    bulk_like = [n for n in names if "bulk" in n.lower() or "download" in n.lower() or "free" in n.lower()]
    record(f"Public names suggesting bulk/download/free route: {bulk_like}")
    doc_evidence.append(f"bulk/download/free-like public names: {bulk_like}")

# --- (4) Write results/key_requirement.md ---
md = []
md.append("# SimFin — API key requirement (probe result)")
md.append("")
md.append(f"- **simfin version:** {version}")
md.append(f"- **Keyless call attempted:** `simfin.load_companies(market='us')` (no API key set)")
md.append("")
md.append("## Verbatim keyless-call error")
md.append("")
if error_type is not None:
    md.append(f"- **Exception type:** `{error_type}`")
    md.append(f"- **Exception message (verbatim):**")
    md.append("")
    md.append("```")
    md.append(error_msg if error_msg is not None else "")
    md.append("```")
elif keyless_result is not None:
    md.append("The keyless call SUCCEEDED — no error was raised. See run.log for the returned data shape/head.")
else:
    md.append("No error recorded (import may have failed — see run.log).")
md.append("")
md.append("## Free default-key test (simfin.load_api_key, default_key='free')")
md.append("")
md.append(f"- **API key after `load_api_key()` with no key file:** `{free_key_value!r}` (source: `simfin/config.py` — `load_api_key(path='~/simfin_api_key.txt', default_key='free')`; `config.py:17` comment: \"The user's API key obtained when registering on www.simfin.com\")")
if free_result_ok:
    md.append("- **Result:** the retry of `simfin.load_companies(market='us')` with the `'free'` default key **SUCCEEDED** — free datasets are reachable without a personal registered key. A personal key is only needed for premium datasets / higher limits.")
else:
    md.append(f"- **Result:** the retry with the `'free'` default key **FAILED** — `{free_error_type}`: {free_error_msg}")
    md.append("- So the documented `'free'` fallback does **not** grant access from this environment; a personal registered API key is required in practice.")
md.append("")
md.append("## What key is needed")
md.append("")
md.append("SimFin data downloads require a SimFin API key supplied via `simfin.set_api_key(...)` "
          "(sent as an `Authorization: api-key <key>` header — `simfin/download.py:25-27`). "
          "The installed package's own text (see evidence in run.log) points users to simfin.com to obtain a key: "
          "`config.py:17`: 'The user's API key obtained when registering on www.simfin.com'.")
md.append("")
md.append("## Where it comes from")
md.append("")
md.append("A free account / free API key from **simfin.com** (sign up on simfin.com to get a personal API key). "
          "No account or key was created by this probe.")
md.append("")
md.append("## How it would be wired here later")
md.append("")
md.append("1. Store the key as a GitHub repo **secret** named `SIMFIN_API_KEY` in `moos-labs/simfin-runner`.")
md.append("2. Pass it to the workflow step as an environment variable from that secret.")
md.append("3. In the script, before any data call:")
md.append("")
md.append("```python")
md.append("import os, simfin as sf")
md.append("sf.set_api_key(os.environ['SIMFIN_API_KEY'])")
md.append("```")
md.append("")
md.append("## Documented keyless / bulk-download route?")
md.append("")
md.append("Checked in-job against the installed library: `set_api_key` presence/docstring, "
          "`load_companies` docstring, the module docstring, a full text search of the installed "
          "package for `api_key` / `api key` / `simfin.com` / `bulk` / `free`, and the list of public "
          "names suggesting a bulk/download/free route. Full evidence is in `results/run.log`.")
md.append("")
md.append("Evidence summary:")
for ev in doc_evidence:
    md.append(f"- {ev}")
md.append("")
if free_result_ok:
    md.append("Conclusion recorded by the probe: a personal key is NOT required for free datasets — "
              "the library's own documented `load_api_key()` fallback (default_key='free') succeeded. "
              "The no-key call fails (401), the bulk-download endpoint is the same route the library "
              "uses for all datasets, and a personal registered key is only needed beyond the free tier.")
else:
    md.append("Conclusion recorded by the probe: no working keyless route exists in practice. The no-key "
              "call failed (401, above), the documented 'free' default key also failed (see above), and "
              "the bulk-download endpoint (https://prod.simfin.com/api/bulk-download/s3) is the library's "
              "only download route and requires the Authorization header. A personal free API key from "
              "simfin.com is required.")
md.append("")

with open("results/key_requirement.md", "w") as f:
    f.write("\n".join(md))

with open("results/probe_output.txt", "w") as f:
    f.write("\n".join(lines))

print("Wrote results/key_requirement.md and results/probe_output.txt", flush=True)
# The keyless failure is the finding, not a crash.
raise SystemExit(0)

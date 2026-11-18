---
name: evidence-walkthrough
description: Run the reference end-to-end research pass — fixed database query, local analysis, artifacts with lineage, then an exported evidence package that verifies in a clean environment. Use as the first-run demonstration, as a benchmark case, or when a result must be handed to someone who was not there when it ran.
origin: openai4s
category: research-workflow
compatibility: The retrieval step needs outbound network access to the UniProt REST API; everything after it is deterministic and offline.
metadata:
  tool_type: python
  primary_tool: urllib (stdlib)
  third_party:
    name: PKU-YuanGroup/OpenAI4S
    repository: https://github.com/PKU-YuanGroup/OpenAI4S
    commit: c965ab3ea89032adb40ac657e24f73a19b4e0be3
    license: MIT
---

# Evidence walkthrough

The reference pass a result has to survive: **query → analyse → artifacts with
lineage → an evidence package a stranger can verify.**

Its point is not the science, which is deliberately small. Its point is that
every step leaves evidence, and the package at the end can be checked by
someone who does not trust this machine — a reviewer, a colleague, or you on a
different laptop in six months.

This port runs without a host runtime: artifacts are plain files in an
`evidence/` directory, and an `evidence/artifacts.jsonl` ledger records every
artifact's hash, the provenance of what it came from, and the lineage edges to
its inputs. The ledger **is** the evidence; a file that never got a ledger
entry might as well not exist.

## Fixed inputs

Use these exact accessions. They are fixed so two runs are comparable and so
this doubles as a benchmark case; changing them makes a run incomparable to
every previous one.

```python
ACCESSIONS = ["P69905", "P68871", "P02042", "P02100"]   # human haemoglobin subunits
```

## Workflow

### 1. Retrieve, and record what you retrieved

```python
import hashlib, json, time, urllib.request
from pathlib import Path

records = []
for accession in ACCESSIONS:
    url = f"https://rest.uniprot.org/uniprotkb/{accession}.json"
    with urllib.request.urlopen(url, timeout=30) as resp:
        body = resp.read()
    record = json.loads(body)
    record["_provenance"] = {
        "database": "uniprot",
        "request_url": url,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "response_sha256": hashlib.sha256(body).hexdigest(),
    }
    records.append(record)

# Check before saving, not after: an artifact written with three quarters of
# its evidence missing is already wrong by the time anyone can query it.
for accession, record in zip(ACCESSIONS, records):
    envelope = record["_provenance"]
    assert accession in envelope["request_url"], accession
    assert envelope["retrieved_at"] and envelope["response_sha256"]
```

Save the raw response **before** analysing it. The analysis is a claim; the raw
response is the evidence for it, and a claim whose evidence was never written
down cannot be rechecked later.

The provenance envelope is the other half. Every retrieval gets one naming the
database, the exact request, the moment it was fetched and a hash of the bytes
that came back — with it the artifact can answer *when was this true* and *was
it the same data*; without it a saved file records what you have but not what
it is evidence of, and a rerun that quietly returned something different is
indistinguishable from one that did not.

```python
evidence = Path("evidence")
evidence.mkdir(exist_ok=True)
LEDGER = evidence / "artifacts.jsonl"

def save_artifact(artifact_id, file_name, *, source=None, inputs=()):
    data = (evidence / file_name).read_bytes()
    entry = {
        "id": artifact_id,
        "file": file_name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": source,
        "inputs": list(inputs),
    }
    with open(LEDGER, "a") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry

raw_bytes = json.dumps(records, indent=2).encode()
(evidence / "raw_uniprot.json").write_bytes(raw_bytes)
raw = save_artifact(
    "raw_uniprot",
    "raw_uniprot.json",
    # EVERY retrieval, not the first one. This file is the evidence for four
    # independent requests, and `records[0]["_provenance"]` describes exactly
    # one of them — the other three accessions would then sit inside an
    # artifact that claims to preserve their evidence while carrying no
    # request URL, no retrieval time and no response hash for them.
    source={
        "kind": "aggregate",
        "database": "uniprot",
        "queries": ACCESSIONS,
        "sources": [record["_provenance"] for record in records],
    },
)
```

One artifact, four retrievals, so **four envelopes**. The aggregate above is
the form to use whenever a file is assembled from more than one request: a
single envelope covers a single request, and attaching one of four is worse
than attaching none — the artifact then looks provenanced while three quarters
of it is unaccounted for. Read it back and confirm every accession is there:

```python
attached = next(
    json.loads(line) for line in open(LEDGER) if json.loads(line)["id"] == "raw_uniprot"
)["source"]
covered = {envelope["request_url"] for envelope in attached["sources"]}
missing = [a for a in ACCESSIONS if not any(a in url for url in covered)]
assert not missing, f"no retrieval provenance attached for {missing}"
```

### 2. Analyse

Keep it to what the raw file supports. Length, mass, and sequence composition
are properties of the record; anything requiring a source you did not save is
a claim you cannot back.

```python
import collections

rows = []
for record in records:
    sequence = (record.get("sequence") or {}).get("value", "")
    rows.append({
        "accession": record.get("primaryAccession"),
        "name": record.get("proteinDescription", {}).get(
            "recommendedName", {}).get("fullName", {}).get("value"),
        "length": len(sequence),
        "top_residues": collections.Counter(sequence).most_common(3),
    })
```

### 3. Produce artifacts, declaring their inputs

```python
(evidence / "summary.json").write_text(json.dumps(rows, indent=2))
summary = save_artifact("summary", "summary.json", inputs=[raw["id"]])
```

`inputs` is the lineage edge. Without it the summary is a file that appeared
from nowhere; with it, anyone reading the ledger can walk back to the exact
bytes it was derived from. Declare it on **every** derived artifact, including
figures.

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6, 3.2))
ax.bar([r["accession"] for r in rows], [r["length"] for r in rows])
ax.set_ylabel("residues")
ax.set_title("Haemoglobin subunit lengths")
fig.tight_layout()
fig.savefig(evidence / "lengths.png", dpi=150)
plt.close(fig)

save_artifact("lengths", "lengths.png", inputs=[raw["id"]])
```

### 4. Export and verify

Pack the evidence directory and verify it the way a recipient would — with a
fresh process that only sees the zip:

```
python skills/evidence-walkthrough/scripts/evidence_package.py make evidence evidence.zip
python skills/evidence-walkthrough/scripts/evidence_package.py verify evidence.zip
```

A pass means every listed file matches its recorded hash and the package
contents match the manifest exactly. It does **not** establish who produced
the package; that needs a signature, which this format does not carry. Say
"verified intact", not "verified authentic".

## What to check before calling it done

- Every derived artifact declares `inputs`. A missing edge is the difference
  between a result and an anecdote.
- The raw retrieval is saved as its own artifact, not just parsed in memory.
- `evidence_package.py verify` exits 0 on the exported package.
- Numbers in your summary can each be traced to a saved file.

## Offline and reproducibility

The retrieval step needs the network. Everything after it is deterministic
given the same raw file, so a benchmark run should fix the raw artifact and
replay from step 2 — that separates "the analysis changed" from "the upstream
database changed", which are different failures and only one of them is yours.

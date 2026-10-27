"""Manifest-driven, offline-by-default source verification; no delivered writes.

Default CLI prints a dry-run plan. Offline --verify writes immutable review
reports. Optional --allow-network requires explicit IDs, a 1..8 match batch limit
and a dedicated evidence store. Existing raw source artifacts are never edited.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import uuid

from src.statsbomb_participation import SourceDocument, adapt_match, _id

SCHEMA = "source-verification-manifest/v1"
MAX_BYTES = 20 * 1024 * 1024
CLOCK_REFERENCE = "retained StatsBomb Events v4.0.0 and v1.1; checked period-local timestamps and Half Start zero origins; minute offsets 0/45"


class EvidenceConflict(ValueError):
    """Conflicting bytes or declarations; never select an arbitrary winner."""


def encode(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Fraction):
        return {"numerator": value.numerator, "denominator": value.denominator}
    raise TypeError(type(value).__name__)


def payload(value):
    return (json.dumps(value, default=encode, sort_keys=True, indent=2, ensure_ascii=True,
                       allow_nan=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_new(path, value):
    path = Path(path)
    with path.open("xb") as stream:
        stream.write(payload(value))


def now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    from src.statsbomb_participation import _pairs
    return json.loads(Path(path).read_bytes(), object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def endpoint(revision, kind, mid):
    return f"https://raw.githubusercontent.com/statsbomb/open-data/{revision}/data/{kind}/{mid}.json"


def bound_document(binding):
    if not isinstance(binding, dict) or not re.fullmatch(r"[a-f0-9]{64}", binding.get("sha256", "")):
        raise ValueError("byte-bound artifact descriptor required")
    path = Path(binding["path"])
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("missing/oversized artifact")
    raw = path.read_bytes()
    if digest(raw) != binding["sha256"]:
        raise EvidenceConflict("artifact fingerprint mismatch: " + str(path))
    doc = SourceDocument(raw, binding["source_reference"], binding["provider_revision"])
    doc.records()
    stamp = binding.get("retrieved_at")
    if not isinstance(stamp, str) or datetime.fromisoformat(stamp).tzinfo is None:
        raise ValueError("explicit timezone-aware retrieval timestamp required")
    return doc


def load_manifest(path):
    data = load_json(path)
    if data.get("schema_version") != SCHEMA or not re.fullmatch(r"[a-f0-9]{40}", data.get("provider_revision", "")):
        raise ValueError("explicit immutable provider revision required")
    if not isinstance(data.get("matches"), list) or not data["matches"]:
        raise ValueError("explicit nonempty fixture inventory required")
    fixtures = {}
    for name, binding in data["fixture_documents"].items():
        if binding["provider_revision"] != data["provider_revision"]:
            raise EvidenceConflict("fixture revision disagreement")
        fixtures[name] = bound_document(binding).records()
    seen = set()
    for row in data["matches"]:
        mid = _id(row["match_id"])
        if mid in seen:
            raise EvidenceConflict("duplicate manifest match ID")
        seen.add(mid)
        matches = [f for f in fixtures[row["fixture_document"]] if f.get("match_id") == mid]
        if len(matches) != 1:
            raise EvidenceConflict("match missing/duplicated in bound fixture document")
        fixture = matches[0]
        if (fixture["competition"]["competition_name"], fixture["season"]["season_name"]) != (row["competition_name"], row["season_name"]):
            raise EvidenceConflict("manifest/fixture context disagreement")
        if set(row.get("artifacts", {})) - {"events", "lineups"}:
            raise ValueError("unsupported artifact kind")
        for kind, binding in row.get("artifacts", {}).items():
            if binding["provider_revision"] != data["provider_revision"] or binding["source_reference"] != endpoint(data["provider_revision"], kind, mid):
                raise EvidenceConflict("artifact endpoint/revision disagreement")
    return data


def manifest_from_phase1(root):
    """Bind every explicit provider fixture; reference retained pilot bytes only."""
    root = Path(root)
    revision = load_json(root / "revision.json")["sha"]

    def binding(name):
        request = load_json(root / (name + ".request.json"))
        path = root / name
        if request["outcome"] != "success" or digest(path.read_bytes()) != request["sha256"]:
            raise EvidenceConflict("retained request/artifact disagreement")
        return dict(path=str(path.resolve()), sha256=request["sha256"],
                    source_reference=request["url"], provider_revision=request["provider_revision"],
                    retrieved_at=request["retrieved_at"])

    documents, rows = {}, []
    selected = set(load_json(root / "selection.json"))
    for file in sorted(root.glob("matches-*.json")):
        if file.name.endswith(".request.json"):
            continue
        documents[file.name] = binding(file.name)
        for fixture in load_json(file):
            mid = fixture["match_id"]
            rows.append(dict(match_id=mid, competition_name=fixture["competition"]["competition_name"],
                             season_name=fixture["season"]["season_name"], fixture_document=file.name,
                             inclusion_policy="pending_team_approval_missing_delivered_fixture" if mid == 3879594 else "no_production_inclusion_authorized",
                             artifacts={kind:binding(f"{kind}-{mid}.json") for kind in ("events", "lineups")} if mid in selected else {}))
    return dict(schema_version=SCHEMA, provider_revision=revision, created_at=now(),
                scope="provider list only; no league completeness or production trust implied",
                fixture_documents=documents, matches=sorted(rows, key=lambda r:r["match_id"]))


def code_revision():
    paths = [Path(__file__), Path(__file__).parents[1]/"src/statsbomb_participation.py",
             Path(__file__).parents[1]/"src/participation_intervals.py"]
    return digest(payload({p.name:digest(p.read_bytes()) for p in paths}))


class EvidenceStore:
    """Append-only request journal and byte-bound immutable reports.

    Interrupted starts stay outcome-unknown. Resume reuses only completed,
    fingerprint-checked artifacts. Orphan/partial objects never become evidence.
    """
    def __init__(self, root, manifest_path, *, create=True):
        self.root = Path(root)
        self.manifest_path = Path(manifest_path)
        self.manifest = load_manifest(manifest_path)
        self.manifest_sha = digest(self.manifest_path.read_bytes())
        marker = self.root / "store.json"
        expected = dict(schema_version="source-verification-store/v1", manifest_sha256=self.manifest_sha)
        if self.root.exists():
            if not marker.is_file() or load_json(marker) != expected:
                raise EvidenceConflict("destination is not this manifest's dedicated evidence store")
        else:
            if not create:
                raise ValueError("resume store does not exist")
            self.root.mkdir(parents=True, exist_ok=False)
            write_new(marker, expected)
        for name in ("journal", "objects", "reports"):
            if create:
                (self.root / name).mkdir(exist_ok=True)
            elif not (self.root/name).is_dir():
                raise EvidenceConflict("incomplete dedicated store layout")
        self.rows = {r["match_id"]:r for r in self.manifest["matches"]}

    def journal(self):
        return [load_json(f) for f in sorted((self.root/"journal").glob("*.json"))]

    def record(self, value):
        write_new(self.root/"journal"/(uuid.uuid4().hex+".json"), value)

    def accounting(self):
        entries=self.journal()
        started={r['request_id'] for r in entries if r.get('outcome')=='started'}
        finished={r['request_id'] for r in entries if r.get('outcome') in ('success','failure')}
        return dict(successes=sum(r.get('outcome')=='success' for r in entries),
                    failures=sum(r.get('outcome')=='failure' for r in entries),
                    interrupted_outcome_unknown=len(started-finished))

    def bindings(self, mid):
        row = self.rows[mid]
        values = {kind:[b] for kind,b in row.get("artifacts", {}).items()}
        for item in self.journal():
            if item.get("match_id") == mid and item.get("outcome") == "success":
                kind = item["kind"]
                b = item["binding"]
                if kind not in ("events", "lineups") or b["source_reference"] != endpoint(self.manifest["provider_revision"],kind,mid) or b["provider_revision"] != self.manifest["provider_revision"]:
                    raise EvidenceConflict("journal endpoint/revision disagreement")
                object_path = Path(b["path"]).resolve()
                if not object_path.is_relative_to((self.root/"objects").resolve()):
                    raise EvidenceConflict("journal artifact escaped dedicated store")
                values.setdefault(kind, []).append(b)
        result = {}
        for kind, bindings in values.items():
            for binding in bindings:
                bound_document(binding)
            if len({b["sha256"] for b in bindings}) != 1:
                raise EvidenceConflict(f"repeat retrieval bytes conflict: {mid}/{kind}")
            result[kind] = sorted(bindings, key=lambda b:(b["retrieved_at"],b["path"]))[0]
        return result

    def _fetch(self, mid, kind, transport):
        request_id = uuid.uuid4().hex
        url = endpoint(self.manifest["provider_revision"],kind,mid)
        start = dict(request_id=request_id, match_id=mid, kind=kind,
                     source_reference=url, requested_at=now())
        self.record({**start, "outcome":"started"})
        try:
            raw = transport(url)
            if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
                raise ValueError("bounded original response bytes required")
            sha = digest(raw)
            obj = self.root/"objects"/(sha+".json")
            if obj.exists():
                if obj.read_bytes() != raw:
                    raise EvidenceConflict("existing object bytes disagree with content fingerprint")
            else:
                with obj.open("xb") as stream:
                    stream.write(raw)
            binding = dict(path=str(obj.resolve()), sha256=sha, source_reference=url,
                           provider_revision=self.manifest["provider_revision"], retrieved_at=now())
            bound_document(binding)
            self.record({**start,"outcome":"success","binding":binding})
        except Exception as exc:
            self.record({**start,"outcome":"failure","error":f"{type(exc).__name__}: {exc}"})
            return False
        return True

    def verify(self, mid):
        row = self.rows[mid]
        bindings = self.bindings(mid)
        if set(bindings) != {"events", "lineups"}:
            return dict(match_id=mid,status="SOURCE_PAIR_INCOMPLETE",missing=sorted({"events","lineups"}-set(bindings)))
        fixture = self.manifest["fixture_documents"][row["fixture_document"]]
        key = digest(payload(dict(match_id=mid, fixture=fixture, artifacts=bindings,
                                  validator_revision=code_revision(), clock_reference=CLOCK_REFERENCE)))
        for path in sorted((self.root/"reports").glob(f"{mid}-*.json")):
            raw = path.read_bytes()
            if digest(raw) != path.stem.split("-",1)[1]:
                raise EvidenceConflict("cached report fingerprint mismatch")
            report = load_json(path)
            if report.get("verification_key") == key and report["artifact_validation"] == "BYTE_BOUND_SOURCE_SCHEMA_REVIEWED":
                return dict(match_id=mid,status="SKIPPED_PREVIOUSLY_VALIDATED_ARTIFACTS",report_path=str(path),report=report)
        docs = [bound_document(b) for b in (fixture, bindings["lineups"], bindings["events"])]
        try:
            adapted = adapt_match(mid, *docs, clock_document_reference=CLOCK_REFERENCE)
            if (adapted.competition_name,adapted.season_name) != (row["competition_name"],row["season_name"]):
                raise EvidenceConflict("adapted context differs from manifest")
            results = adapted.validate()
            players = [dict(player=asdict(p),validation=asdict(r)) for p,r in zip(adapted.players,results)]
            report = dict(schema_version="source-match-review/v1",verification_key=key,match_id=mid,
                          competition_name=adapted.competition_name,season_name=adapted.season_name,
                          artifact_validation="BYTE_BOUND_SOURCE_SCHEMA_REVIEWED",artifacts=bindings,
                          fixture_document=fixture,clock_policy=asdict(adapted.policy),
                          boundaries=[asdict(b) for b in adapted.boundaries],warnings=adapted.warnings,
                          players=players,inclusion_policy=row["inclusion_policy"],
                          active_status_counts=dict(Counter(r.status for p,r in zip(adapted.players,results) if p.observations or p.source_checks)),
                          production_certified=False,source_independently_verified=False,
                          publication_authorized=False)
        except (ValueError, KeyError, TypeError) as exc:
            report = dict(schema_version="source-match-review/v1",verification_key=key,match_id=mid,
                          artifact_validation="SOURCE_REJECTED",error=f"{type(exc).__name__}: {exc}",
                          artifacts=bindings,production_certified=False,publication_authorized=False)
        return self.save_report(mid,report)

    def save_report(self, mid, report):
        raw = payload(report)
        path = self.root/"reports"/f"{mid}-{digest(raw)}.json"
        if path.exists():
            if path.read_bytes() != raw:
                raise EvidenceConflict("existing report conflicts with its content fingerprint")
        else:
            with path.open("xb") as stream:
                stream.write(raw)
        return dict(match_id=mid,status=report["artifact_validation"],report_path=str(path),report=json.loads(raw))

    def execute(self, match_ids, *, allow_network=False, batch_limit=None, refresh=False, transport=None):
        if not isinstance(match_ids,list) or not match_ids or any(type(i) is not int for i in match_ids) or len(set(match_ids))!=len(match_ids) or not set(match_ids)<=self.rows.keys():
            raise ValueError("explicit unique manifest fixture IDs required")
        if allow_network is not False and allow_network is not True:
            raise ValueError("explicit boolean network authorization required")
        if allow_network:
            if type(batch_limit) is not int or not 1 <= batch_limit <= 8 or len(match_ids)>batch_limit:
                raise ValueError("explicit 1..8 match batch limit required for retrieval")
        elif refresh or transport is not None:
            raise ValueError("network transport/refresh requires explicit network authorization")
        if len(match_ids)>64:
            raise ValueError("verification batch capped at 64 matches")
        results=[]
        for mid in sorted(match_ids):
            try:
                bindings=self.bindings(mid)
                if allow_network:
                    for kind in ("events","lineups"):
                        if refresh or kind not in bindings:
                            self._fetch(mid,kind,transport or public_transport)
                results.append(self.verify(mid))
            except (ValueError,KeyError,OSError) as exc:
                error=f"{type(exc).__name__}: {exc}"
                report=dict(schema_version='source-integrity-conflict/v1',match_id=mid,
                            artifact_validation='SOURCE_EVIDENCE_CONFLICT',error=error,
                            declared_artifacts=self.rows[mid].get('artifacts',{}),
                            journal=sorted([r for r in self.journal() if r.get('match_id')==mid],
                                           key=lambda r:(r.get('request_id',''),r.get('outcome',''))),
                            production_certified=False,publication_authorized=False)
                results.append({**self.save_report(mid,report),'error':error})
        return results


def public_transport(url):
    # Imported and called only after the explicit network authorization gate.
    import urllib.request
    with urllib.request.urlopen(url,timeout=45) as response:
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:
            raise ValueError("response byte cap exceeded")
        return raw


def dry_run(manifest_path, *, destination=None, match_ids=None):
    manifest=load_manifest(manifest_path)
    ids={r['match_id'] for r in manifest['matches']}
    if match_ids is not None and (not isinstance(match_ids,list) or not match_ids or any(type(i) is not int for i in match_ids) or len(set(match_ids))!=len(match_ids) or not set(match_ids)<=ids):
        raise ValueError('explicit unique manifest fixture IDs required')
    selected=ids if match_ids is None else set(match_ids)
    store=EvidenceStore(destination,manifest_path,create=False) if destination is not None and Path(destination).exists() else None
    ready=[];conflicts=[]
    for row in manifest["matches"]:
        mid=row['match_id']
        if mid not in selected:
            continue
        try:
            bindings=store.bindings(mid) if store else row.get('artifacts',{})
            for binding in bindings.values():
                bound_document(binding)
            if set(bindings)=={'events','lineups'}:
                ready.append(mid)
        except (ValueError,KeyError,OSError) as exc:
            conflicts.append(dict(match_id=mid,error=f'{type(exc).__name__}: {exc}'))
    return dict(mode="OFFLINE_DRY_RUN",network_enabled=False,fixture_count=len(manifest["matches"]),selected_fixture_count=len(selected),
                obtained_match_pair_ids=ready,additional_match_pairs_required=len(selected)-len(ready),
                integrity_conflicts=conflicts,request_accounting=store.accounting() if store else None,
                production_certified_contexts=0)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",required=True,type=Path)
    parser.add_argument("--verify",action="store_true")
    parser.add_argument("--allow-network",action="store_true")
    parser.add_argument("--match-ids",type=int,nargs="+")
    parser.add_argument("--batch-limit",type=int)
    parser.add_argument("--destination",type=Path)
    parser.add_argument("--refresh",action="store_true")
    args=parser.parse_args(argv)
    try:
        if not args.verify and not args.allow_network:
            if args.refresh:
                raise ValueError("refresh requires explicit network authorization")
            plan=dry_run(args.manifest,destination=args.destination,match_ids=args.match_ids)
            print(json.dumps(plan,sort_keys=True,indent=2));return 1 if plan['integrity_conflicts'] else 0
        if args.destination is None or args.match_ids is None:
            raise ValueError("explicit dedicated destination and match IDs required")
        # Validate retrieval authorization before creating any store directories.
        if args.allow_network and (type(args.batch_limit) is not int or not 1<=args.batch_limit<=8 or len(args.match_ids)>args.batch_limit):
            raise ValueError("explicit small --batch-limit 1..8 required")
        store=EvidenceStore(args.destination,args.manifest)
        results=store.execute(args.match_ids,allow_network=args.allow_network,batch_limit=args.batch_limit,refresh=args.refresh)
        print(json.dumps([{k:v for k,v in r.items() if k!='report'} for r in results],indent=2))
        return 1 if any(r['status'] in ('SOURCE_EVIDENCE_CONFLICT','SOURCE_PAIR_INCOMPLETE','SOURCE_REJECTED') or r.get('report',{}).get('active_status_counts',{}).get('CONFLICTING_EVIDENCE',0) for r in results) else 0
    except (ValueError,KeyError,OSError) as exc:
        print(f"Source verification rejected: {exc}");return 2


if __name__=="__main__":
    raise SystemExit(main())

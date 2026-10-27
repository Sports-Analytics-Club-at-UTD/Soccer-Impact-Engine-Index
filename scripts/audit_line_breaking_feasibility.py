"""Read-only, bounded 360/event coverage audit. No candidate scores or dataset outputs.

Temporary SQLite indexes hold event/frame summaries; input Parquets stay read-only.
Use python -B -m scripts.audit_line_breaking_feasibility with explicit paths.
"""
import argparse
from collections import Counter, defaultdict
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import sys
import tempfile

import pyarrow.parquet as pq

from src.identity import _ids
from src.line_breaking_candidates import FRAME_COLUMNS, LineBreakingError, _point, frame_quality

EVENT_COLUMNS=["id","match_id","competition_name","season_name","type","location",
               "pass_end_location","pass_type","pass_outcome","ball_recovery_recovery_failure"]
TARGET_LEAGUES=("La Liga","Premier League","Serie A","Ligue 1")


def _rows(path,columns,batch_size):
    for batch in pq.ParquetFile(path).iter_batches(columns=columns,batch_size=batch_size):
        values=batch.to_pydict()
        yield batch,zip(*(values[c] for c in columns))


def _key(event_id,mid,comp,season):
    if (not isinstance(event_id,str) or not event_id.strip() or type(mid) is not int or not 0<mid<=2**63-1
            or not isinstance(comp,str) or not comp.strip() or not isinstance(season,str) or not season.strip()):
        raise ValueError("invalid source event/match/competition/season identity")


def _geometry(location):
    if location is None or len(location)<2: return None,0
    try: value=_point(location[:2])
    except LineBreakingError: return None,2
    return value,1 if value is not None else 0


def audit_files(*,events_path,frames_path,actor_tolerance,batch_size=16384,scratch_dir=None,progress=None):
    if type(batch_size) is not int or not 0<batch_size<=65536: raise ValueError("batch size must be 1..65536")
    if isinstance(actor_tolerance,bool) or not isinstance(actor_tolerance,(int,float)) or not math.isfinite(actor_tolerance) or actor_tolerance<0:
        raise ValueError("explicit finite nonnegative actor tolerance required")
    for path in (events_path,frames_path):
        if not Path(path).is_file(): raise FileNotFoundError(f"Required input unavailable: {path}")
    frame_file=pq.ParquetFile(frames_path); event_file=pq.ParquetFile(events_path)
    nulls=Counter(); row_slots=Counter(); frame_matches=defaultdict(set); event_matches=defaultdict(set)
    failure_flags=Counter(); frame_quality_reasons=Counter(); frame_points=Counter(); current=None; carry=[]; pending=[]
    total_frame_rows=0; max_frame_rows=128
    with tempfile.TemporaryDirectory(dir=scratch_dir) as temporary:
        with closing(sqlite3.connect(str(Path(temporary)/"coverage.sqlite"))) as db:
            db.execute("PRAGMA journal_mode=OFF"); db.execute("PRAGMA synchronous=OFF")
            db.execute("PRAGMA cache_size=-65536"); db.execute("PRAGMA temp_store=FILE")
            # Append first; bulk-build sorted indexes after collection. Incremental
            # random UUID primary-key insertion needlessly amplifies disk work.
            db.execute("CREATE TABLE frame_blocks(id TEXT, mid INTEGER, comp TEXT, season TEXT, nrows INTEGER, duplicates INTEGER, actors INTEGER, ax REAL, ay REAL, usable INTEGER)")
            db.execute("CREATE TABLE events(id TEXT, mid INTEGER, comp TEXT, season TEXT, kind TEXT, open_pass INTEGER, completed INTEGER, geom INTEGER, x0 REAL, y0 REAL, x1 REAL, y1 REAL)")
            def flush():
                if not pending: return
                db.executemany("INSERT INTO frame_blocks VALUES (?,?,?,?,?,?,?,?,?,?)",pending)
                pending.clear()
            def finish():
                if current is None: return
                signatures=Counter((r["teammate"],r["actor"],r["keeper"],tuple(r["location"]) if r["location"] is not None else None) for r in carry)
                duplicates=sum(n-1 for n in signatures.values() if n>1)
                actors=[r for r in carry if r["actor"] is True]
                try: quality=frame_quality(carry)
                except LineBreakingError as exc:
                    quality={"structurally_usable":False,"reasons":("invalid_frame_numeric_or_flags",),"actor_location":None}
                if len(carry)>max_frame_rows:
                    quality={"structurally_usable":False,"reasons":("frame_row_limit_exceeded",),"actor_location":None}
                frame_quality_reasons.update(quality["reasons"])
                actor=quality["actor_location"] if len(actors)==1 else None
                pending.append((*current,len(carry),duplicates,len(actors),actor[0] if actor else None,actor[1] if actor else None,int(quality["structurally_usable"])))
                if len(pending)>=1000: flush()
            for batch,rows in _rows(frames_path,FRAME_COLUMNS,batch_size):
                previous=total_frame_rows
                total_frame_rows+=len(batch)
                nulls.update({c:batch.column(i).null_count for i,c in enumerate(FRAME_COLUMNS)})
                for values in rows:
                    row=dict(zip(FRAME_COLUMNS,values)); key=tuple(row[c] for c in ("id","match_id","competition_name","season_name"))
                    _key(*key)
                    slot=(key[2],key[3]); row_slots[slot]+=1; frame_matches[slot].add(key[1])
                    try: point=_point(row["location"])
                    except LineBreakingError: frame_points["invalid_or_off_pitch"]+=1
                    else:
                        if point is None: frame_points["missing_coordinates"]+=1
                    if key!=current:
                        finish(); current=key; carry=[]
                    carry.append(row)
                    if len(carry)>max_frame_rows+1:
                        raise ValueError("single-frame memory bound exceeded; no truncated audit")
                if progress and previous//1000000!=total_frame_rows//1000000: progress(f"360 observation rows scanned: {total_frame_rows}")
            finish(); flush(); db.commit()
            if progress: progress("Building frame-event summary index")
            db.execute("""CREATE TABLE frames AS SELECT id,
                CASE WHEN min(mid)=max(mid) AND min(comp)=max(comp) AND min(season)=max(season) THEN min(mid) END mid,
                CASE WHEN min(mid)=max(mid) AND min(comp)=max(comp) AND min(season)=max(season) THEN min(comp) END comp,
                CASE WHEN min(mid)=max(mid) AND min(comp)=max(comp) AND min(season)=max(season) THEN min(season) END season,
                sum(nrows) nrows,sum(duplicates) duplicates,sum(actors) actors,
                CASE WHEN count(*)=1 THEN min(ax) END ax,CASE WHEN count(*)=1 THEN min(ay) END ay,
                CASE WHEN count(*)=1 THEN min(usable) ELSE 0 END usable,count(*) blocks,
                (min(mid)!=max(mid) OR min(comp)!=max(comp) OR min(season)!=max(season)) conflict
                FROM frame_blocks GROUP BY id""")
            db.execute("CREATE UNIQUE INDEX frame_id ON frames(id)")
            scanned_events=0
            for batch,rows in _rows(events_path,EVENT_COLUMNS,batch_size):
                inserts=[]
                for event_id,mid,comp,season,kind,start,end,pass_type,outcome,failure in rows:
                    _key(event_id,mid,comp,season); event_matches[(comp,season)].add(mid)
                    is_pass=kind=="Pass"; is_open=is_pass and (pass_type is None or pass_type in ("Recovery","Interception"))
                    a,ga=_geometry(start) if is_pass else (None,0); b,gb=_geometry(end) if is_pass else (None,0)
                    geometry=2 if 2 in (ga,gb) else 1 if ga==gb==1 else 0
                    inserts.append((event_id,mid,comp,season,kind,int(is_open),int(is_pass and outcome is None),geometry,
                        a[0] if a else None,a[1] if a else None,b[0] if b else None,b[1] if b else None))
                    if kind=="Ball Recovery": failure_flags["failed_true" if failure is True else "explicit_false" if failure is False else "missing_flag_nonfailed_under_M2B"]+=1
                db.executemany("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",inserts)
                previous=scanned_events; scanned_events+=len(inserts)
                if progress and previous//1000000!=scanned_events//1000000: progress(f"Source event rows scanned: {scanned_events}")
            db.commit()
            if progress: progress("Validating event uniqueness and joining pass/frame coverage")
            try: db.execute("CREATE UNIQUE INDEX event_id ON events(id)")
            except sqlite3.IntegrityError as exc: raise ValueError("duplicate source event IDs; no deduplication") from exc
            db.execute("CREATE INDEX event_slot ON events(comp,season)")
            tolerance2=actor_tolerance**2
            native="((f.ax-e.x0)*(f.ax-e.x0)+(f.ay-e.y0)*(f.ay-e.y0))"
            mirrored="((120-f.ax-e.x0)*(120-f.ax-e.x0)+(80-f.ay-e.y0)*(80-f.ay-e.y0))"
            join="FROM events e LEFT JOIN frames f ON f.id=e.id AND f.mid=e.mid AND f.comp=e.comp AND f.season=e.season AND f.conflict=0"
            eligible="e.open_pass=1 AND e.completed=1 AND e.geom=1"
            usable=f"({eligible} AND f.usable=1 AND f.blocks=1 AND f.ax IS NOT NULL)"
            query=f"""SELECT e.comp,e.season,count(*),sum(e.kind='Pass'),sum(e.open_pass),sum(e.open_pass AND e.completed),
                sum({eligible}),sum(e.kind='Pass' AND f.id IS NOT NULL),sum(e.open_pass AND e.completed AND f.id IS NOT NULL),
                sum({eligible} AND f.id IS NOT NULL),sum({eligible} AND f.usable=1),
                sum({usable} AND {native}<=?),sum({usable} AND {native}<=? AND {mirrored}>?),
                sum({usable} AND {native}>? AND {mirrored}<=?),sum({usable} AND {native}<=? AND {mirrored}<=?),
                sum({usable} AND {native}>? AND {mirrored}>?),sum(e.kind='Pass' AND e.geom=0),sum(e.kind='Pass' AND e.geom=2)
                {join} GROUP BY e.comp,e.season ORDER BY e.comp,e.season"""
            names=["competition_name","season_name","event_rows","pass_events","open_play_passes","completed_open_play_passes",
                "completed_open_play_valid_geometry","pass_events_with_frames","completed_open_play_with_frames",
                "completed_open_play_valid_geometry_with_frames","structurally_usable_completed_pass_frames",
                "native_actor_aligned","native_only","mirror_only","ambiguous_native_and_mirror","neither_actor_alignment",
                "missing_pass_geometry","invalid_or_off_pitch_pass_geometry"]
            coverage=[]
            for values in db.execute(query,(tolerance2,)*9).fetchall():
                item=dict(zip(names,values)); slot=(values[0],values[1])
                for name in names[2:]:
                    if item[name] is None: item[name]=0
                item.update(event_matches=len(event_matches[slot]),frame_rows=row_slots[slot],frame_matches=len(frame_matches[slot]),
                    frame_events=db.execute("SELECT count(*) FROM frames WHERE comp=? AND season=?",slot).fetchone()[0],
                    missing_frame_pass_events=item["pass_events"]-item["pass_events_with_frames"],
                    missing_frame_completed_open_play=item["completed_open_play_passes"]-item["completed_open_play_with_frames"],
                    fully_direction_attested_candidate_passes=0)
                n=db.execute(f"SELECT count(*) {join} WHERE e.comp=? AND e.season=? AND {usable}",slot).fetchone()[0]
                median=[]
                if n:
                    for offset in ((n-1)//2,n//2):
                        squared=db.execute(f"SELECT {native} {join} WHERE e.comp=? AND e.season=? AND {usable} ORDER BY {native} LIMIT 1 OFFSET ?",(*slot,offset)).fetchone()[0]
                        median.append(math.sqrt(squared))
                item["actor_distance_sample_count"]=n; item["median_actor_start_distance"]=sum(median)/2 if median else None
                coverage.append(item)
                if progress: progress(f"Coverage summarized: {slot[0]} {slot[1]}")
            frame_only=[]
            for comp,season,n in db.execute("SELECT comp,season,count(*) FROM frames GROUP BY comp,season ORDER BY comp,season"):
                if comp is None or season is None: continue
                frame_only.append({"competition_name":comp,"season_name":season,"frame_rows":row_slots[(comp,season)],"frame_events":n,"matches":len(frame_matches[(comp,season)])})
            summary={"label":"CANDIDATE / DIAGNOSTIC / NOT PRODUCTION APPROVED", "frames_schema":str(frame_file.schema_arrow.remove_metadata()),
                "frame_rows":total_frame_rows,"distinct_frame_events":db.execute("SELECT count(*) FROM frames").fetchone()[0],
                "duplicate_observation_rows":db.execute("SELECT sum(duplicates) FROM frames").fetchone()[0],
                "frame_events_with_duplicate_observations":db.execute("SELECT count(*) FROM frames WHERE duplicates>0").fetchone()[0],
                "repeated_noncontiguous_frame_event_blocks":db.execute("SELECT count(*) FROM frames WHERE blocks>1").fetchone()[0],
                "conflicting_frame_event_contexts":db.execute("SELECT count(*) FROM frames WHERE conflict>0").fetchone()[0],
                "frame_actor_count_distribution":[{"actors":a,"frame_events":n} for a,n in db.execute("SELECT actors,count(*) FROM frames GROUP BY actors ORDER BY actors")],
                "structurally_usable_frame_events":db.execute("SELECT count(*) FROM frames WHERE usable=1 AND blocks=1").fetchone()[0],
                "frame_quality_exclusions":dict(sorted(frame_quality_reasons.items())),"frame_coordinate_exclusions":dict(frame_points),
                "frame_null_counts":dict(sorted(nulls.items())),"frame_slots":frame_only,"coverage":coverage,
                "frame_events_absent_from_filtered_event_source":db.execute("SELECT count(*) FROM frames f LEFT JOIN events e ON e.id=f.id WHERE e.id IS NULL").fetchone()[0],
                "frame_event_context_mismatches":db.execute("SELECT count(*) FROM frames f JOIN events e ON e.id=f.id WHERE f.conflict=1 OR f.mid!=e.mid OR f.comp!=e.comp OR f.season!=e.season").fetchone()[0],
                "source_event_rows":event_file.metadata.num_rows,"unique_source_event_ids":db.execute("SELECT count(*) FROM events").fetchone()[0],
                "failed_ball_recovery_flags":dict(failure_flags),"actor_tolerance":actor_tolerance,
                "orientation_caveat":"native/mirror actor alignment is diagnostic; source contains no independently attested attacking-direction field",
                "player_id_caveat":"no visible-player IDs or observation IDs; duplicate signatures are ambiguity checks, not player identity verification",
                "target_2015_2016":[row for row in coverage if row["competition_name"] in TARGET_LEAGUES and row["season_name"]=="2015/2016"],
                "production_fifth_attribute_ready":False}
    return summary


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events",required=True,type=Path); parser.add_argument("--frames",required=True,type=Path)
    parser.add_argument("--actor-tolerance",required=True,type=float)
    parser.add_argument("--batch-size",default=16384,type=int); parser.add_argument("--scratch-dir",type=Path)
    args=parser.parse_args(argv)
    result=audit_files(events_path=args.events,frames_path=args.frames,actor_tolerance=args.actor_tolerance,
                       batch_size=args.batch_size,scratch_dir=args.scratch_dir,
                       progress=lambda message:print(message,file=sys.stderr,flush=True))
    print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))
    return 0


if __name__=="__main__": raise SystemExit(main())

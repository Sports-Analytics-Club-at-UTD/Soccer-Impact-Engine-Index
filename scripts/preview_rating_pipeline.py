"""Offline synthetic fixture generator. Never reads or exports real measurements."""
import argparse
from pathlib import Path

import pandas as pd

from src.defensive_candidates import DefensivePolicy, POLICY_ID, SOURCE, FORMULA
from src.dri_scoring import Evidence, ComparisonPool, SeasonScope, LEAGUES, SEASON
from src.identity_evidence import SYNTHETIC
from src.press_scoring import SyntheticEvidence, CandidatePolicy, FIFA, PressScope, COUNT_COLS
from src.rating_assembly import PlayerContext
from src.rating_delivery import serialize_delivery
from src.rating_pipeline import synthetic_rating_delivery


def fixture():
    e = Evidence(SYNTHETIC,"invented-phase2-ledger/v1",True)
    pe = SyntheticEvidence(SYNTHETIC,"phase2-fixture/v1",e.source,True)
    pool = ComparisonPool("synthetic-four-league/v1",SYNTHETIC,e)
    policy = DefensivePolicy(POLICY_ID,SOURCE,FORMULA,True)
    press_policy = CandidatePolicy("pratyush-press-sample-z/experiment-v1",
        "f024cbf:src/metrics/press_resistancev2.py; unrounded candidate",FIFA,30,900.,"separate_mid_cb",2,"one_context_per_player")
    pop=[];metrics=[];actions=[];names={}
    for i in range(8):
        c = PlayerContext(900000001+i,f"Invented Club {i+1}",LEAGUES[i%4],SEASON)
        key = dict(player_id=c.player_id,team=c.team,competition_name=c.competition_name,season_name=c.season_name)
        scope = SeasonScope(c.competition_name,SEASON,(800000001+i,),True)
        pop.append(dict(**key,position_group="DM" if i<4 else "CB",reference_member=True,minutes=900.,
            exposure_scope=scope,identity_evidence=e,context_evidence=e,exposure_evidence=e))
        for j,event in enumerate(("Tackle","Interception","Ball Recovery")):
            count = (i%4+1)*(j+1)*10
            metrics.append(dict(**key,event_type=event,count=count,minutes=900.,per90=count/900*90,rate_status="ok",
                numerator_scope=scope,reportable=True,reportability_source=e.source,coverage_evidence=e))
        actions.append(dict(**key,**dict(zip(COUNT_COLS,(40,(i%4+1)*10,0,0))),
            numerator_scope=PressScope(c.competition_name,SEASON,scope.match_ids,True),coverage_evidence=pe))
        names[c] = f"Synthetic Actor {i+1}"
    return dict(population=pd.DataFrame(pop),measurements=pd.DataFrame(metrics),actions=pd.DataFrame(actions),
        pool=pool,defensive_policy=policy,press_policy=press_policy,evidence=pe,names=names)


def demonstration():
    return synthetic_rating_delivery(**fixture())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True,help="new local synthetic JSON file (exclusive creation)")
    args = parser.parse_args()
    result = serialize_delivery(demonstration())
    with args.output.open("x",encoding="utf-8",newline="\n") as target:
        target.write(result)
    print(f"8 invented actors; no real ratings; local preview: {args.output}")


if __name__ == "__main__":
    main()

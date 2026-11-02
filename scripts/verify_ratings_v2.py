"""Run V2/public/authorized retained checks, preserving exact logs and counts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def run():
    out=ROOT/'audit-output/ratings-v2'
    out.mkdir(parents=True,exist_ok=True)
    prior=ROOT.parent/'Soccer-Impact-Engine-Index-identity-source-reconciliation'
    # Provision just the two already-authorized small source-evidence fixtures.
    provisions=[]
    for folder,name in [('chronology-priority','priority-evidence.json'),('event-chronology','current-exception-inventory.csv')]:
        source=prior/'audit-output'/folder/name;target=ROOT/'audit-output'/folder/name
        data=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert target.read_bytes()==data
        else:target.write_bytes(data)
        provisions.append(dict(source=str(source),target=str(target),sha256=hashlib.sha256(data).hexdigest()))
    harness=out/'run-private-backend.py'
    harness.write_text("""import importlib.util,sys,os
from pathlib import Path
new=Path(__file__).resolve().parents[2]
original=new.parent/'Soccer-Impact-Engine-Index'
os.chdir(original)
sys.path[:0]=[str(new),str(original)]
import src,scripts
src.__path__[:]=[str(new/'src'),str(original/'src')]
scripts.__path__[:]=[str(new/'scripts'),str(original/'scripts')]
from scripts import local_experimental_ratings as adapter
adapter.ROOT=original
adapter.PACKAGE=original/'data/derived/private-five-attribute-v2'
spec=importlib.util.spec_from_file_location('private_runner',original/'scripts/run_backend_tests.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
sys.argv=['run_backend_tests.py','private','-q']
raise SystemExit(runner.main())
""",encoding='utf8')
    # The retained frontend harness runs only after all application source and
    # scripts agree. It retains separately reviewed private tests and data.
    frontend=prior/'audit-output/private-suite-checkout/frontend'
    equality=[]
    for folder in ['src','scripts']:
        for path in (ROOT/'frontend'/folder).rglob('*'):
            if not path.is_file():continue
            other=frontend/path.relative_to(ROOT/'frontend')
            a=path.read_bytes().replace(b'\r\n',b'\n');b=other.read_bytes().replace(b'\r\n',b'\n')
            assert a==b,(path,other)
            equality.append(dict(path=str(path),retained_path=str(other),normalized_sha256=hashlib.sha256(a).hexdigest()))
    (out/'test-provisioning-hashes.json').write_text(json.dumps(dict(fixtures=provisions,frontend_equality=equality),indent=2)+'\n',encoding='utf8')
    suites=[
      ('v2-targeted',[sys.executable,'-B','-m','pytest','tests/test_ratings_v2.py','tests/test_participation_decoder_aliases.py','tests/test_off_field_cards.py','tests/test_source_backed_entry.py','tests/test_permanent_exits.py','tests/test_event_chronology.py','tests/test_safe_recovery.py','tests/test_source_reconstruction.py','tests/test_statsbomb_participation.py','tests/test_private_five_attribute.py','tests/test_rating_pipeline.py','-q','-p','no:cacheprovider']),
      ('public-backend',[sys.executable,'-B','-m','scripts.run_backend_tests','public','-q']),
      ('private-backend',[sys.executable,'-B',str(harness)]),
      ('original-source-regressions',[sys.executable,'-B','-m','scripts.check_off_field_card_sources']),
      ('independent-regressions',[sys.executable,'-B',str(ROOT.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/test_independent_audit.py')]),
      ('identity-probes',[sys.executable,'-B','-c',"import src,runpy;runpy.run_path('../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/identity_probes.py',run_name='__main__')"]),
      ('public-frontend',['npm.cmd','run','test:public','--prefix','frontend']),
      ('private-frontend',['npm.cmd','run','test:private','--prefix',str(frontend)]),
      ('production-build',['npm.cmd','run','build','--prefix','frontend'])]
    results={}
    for name,cmd in suites:
        print('Starting '+name,flush=True);start=time.monotonic();log=out/(name+'.log')
        if log.exists():raise ValueError('preserve previous suite log: '+str(log))
        with log.open('x',encoding='utf8') as f:p=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
        text=log.read_text(encoding='utf8',errors='replace');counts=dict(passed=0,failed=0,skipped=0,blocked=0,deselected=0)
        for key in counts:
            m=re.findall(r'(\d+) '+key+r'\b',text)
            if m:counts[key]=int(m[-1])
        for key,label in [('passed','pass'),('failed','fail'),('skipped','skipped')]:
            m=re.findall(r'^(?:#|ℹ) '+label+r' (\d+)',text,re.M)
            if m:counts[key]=int(m[-1])
        m=re.search(r'Ran (\d+) tests?',text)
        if m and '\nOK' in text:counts['passed']=int(m.group(1))
        if name=='production-build' and p.returncode==0:counts['passed']=1
        if name=='identity-probes' and p.returncode==0:counts['passed']=len(json.loads(text)['results'])
        if p.returncode and not counts['failed']:counts['blocked']=1
        results[name]=dict(command=cmd,cwd=str(ROOT),returncode=p.returncode,log=str(log),seconds=time.monotonic()-start,**counts)
        (out/'test-results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
        print(name,counts,flush=True)


if __name__=='__main__':run()

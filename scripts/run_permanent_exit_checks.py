"""Run the public and retained private checks against this local correction."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root=Path.cwd();out=root/'audit-output';out.mkdir(exist_ok=True)
    prior=root.parent/'Soccer-Impact-Engine-Index-source-backed-entry-fix'
    original=root.parent/'Soccer-Impact-Engine-Index'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    receipts={}
    def bind(p):
        receipts[str(p.resolve())]=hashlib.sha256(p.read_bytes()).hexdigest()
    # Provision retained private fixtures without changing any previous checkout.
    private=out/'private-suite-checkout'
    private.mkdir(exist_ok=True)
    for name in ('frontend','scripts','src'):
        shutil.copytree(prior/'audit-output/private-suite-checkout'/name,private/name,
            ignore=shutil.ignore_patterns('node_modules','dist','__pycache__'),dirs_exist_ok=True)
    if not (private/'data').exists():
        subprocess.run(['powershell','-NoProfile','-Command',
            "New-Item -ItemType Junction -Path '"+str(private/'data')+"' -Target '"+str(original/'data')+"' | Out-Null"],check=True)
    def files(folder):
        for parent,dirs,names in os.walk(folder):
            dirs[:]=[d for d in dirs if d not in ('node_modules','dist','__pycache__')]
            for name in names:yield Path(parent)/name
    for path in files(root/'frontend'):
            target=private/'frontend'/path.relative_to(root/'frontend')
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    dependencies=(prior/'frontend/node_modules').resolve()
    for frontend in (root/'frontend',private/'frontend'):
        if not (frontend/'node_modules').exists():
            # Directory junction avoids copying the validated locked dependency tree.
            subprocess.run(['powershell','-NoProfile','-Command',
                "New-Item -ItemType Junction -Path '"+str(frontend/'node_modules')+"' -Target '"+str(dependencies)+"' | Out-Null"],check=True)
    runner=out/'run-private-backend.py'
    runner.write_text('''import importlib.util,sys,os
from pathlib import Path
new=Path(__file__).resolve().parents[1]
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
''',encoding='utf8')
    bind(runner)
    inventory=json.loads((original/'tests/suite_inventory.json').read_text())
    for name,h in inventory['private_source_sha256'].items():
        path=original/name
        assert hashlib.sha256(path.read_text(encoding='utf8').encode()).hexdigest()==h
        bind(path)
    for name in ('frontend','scripts','src'):
        for path in files(private/name):bind(path)
    for path in (root/'frontend/package-lock.json',prior/'frontend/package-lock.json'):bind(path)
    assert (root/'frontend/package-lock.json').read_bytes()==(prior/'frontend/package-lock.json').read_bytes()
    commands=[
        ('targeted-regressions',[sys.executable,'-B','-m','pytest','tests/test_permanent_exits.py','tests/test_source_backed_entry.py','tests/test_off_field_cards.py','tests/test_statsbomb_participation.py','-q','-p','no:cacheprovider']),
        ('original-source-regressions',[sys.executable,'-B','-m','scripts.check_off_field_card_sources']),
        ('public-backend',[sys.executable,'-B','-m','scripts.run_backend_tests','public','-q']),
        ('private-backend',[sys.executable,'-B',str(runner)]),
        ('independent-regressions',[sys.executable,'-B',str(root.parent/'Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/test_independent_audit.py')]),
        ('identity-probes',[sys.executable,'-B','-c',"import src,runpy; runpy.run_path('../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/identity_probes.py',run_name='__main__')"]),
        ('public-frontend',['npm.cmd','run','test:public','--prefix','frontend']),
        ('private-frontend',['npm.cmd','run','test:private','--prefix',str(private/'frontend')]),
        ('production-build',['npm.cmd','run','build','--prefix','frontend']),
    ]
    results={}
    for name,command in commands:
        log=out/(name+'.log')
        if log.exists():raise ValueError('Preserve prior test logs: '+str(log))
        print('Running '+name,flush=True)
        with log.open('w',encoding='utf8') as stream:
            result=subprocess.run(command,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT)
        results[name]=dict(command=command,returncode=result.returncode,log=str(log.relative_to(root)))
        print(name+': exit '+str(result.returncode),flush=True)
    (out/'verification-executions.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
    (out/'private-harness-input-hashes.json').write_text(json.dumps(receipts,indent=2)+'\n',encoding='utf8')


if __name__=='__main__':main()

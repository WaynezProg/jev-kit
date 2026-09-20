"""Small real Codex App Server screen, direct worker versus upstream Foreman."""
import asyncio, json, os, subprocess, sys, time
from pathlib import Path
from foreman.config import FactoryConfig
from foreman.foreman.jev import JevForemanModel
from foreman.runtime import FactoryRuntime
from foreman.models import WorkerRecord
from foreman.workers.codex_app_server import CodexAppServerWorker
from foreman.workers.codex import mission_for
from foreman.models import WorkerType
OUT=Path(sys.argv[1]);OUT.mkdir(parents=True,exist_ok=True)
def save(path,data):
    with path.open('x') as f:json.dump(data,f,indent=2,default=str);f.write('\n')
cases=[dict(id='count',code='def parse_count(s):\n    return int(float(s))\n',job='Fix parse_count(s). Accept only nonempty ASCII digit strings, including 0 and leading zeros. Reject negative, fraction, whitespace, exponent and non-ASCII digit strings with ValueError. Reject non-string inputs with TypeError. Preserve the function API. Add and run unittest tests. Work only in this fixture repository; no network or additional agents.',check="from app import parse_count as f\nassert f('0007') == 7\nassert f('0') == 0\nfor x in ['-1','1.5',' 2','2 ','','1e2','١٢']:\n try: f(x)\n except ValueError: pass\n else: raise AssertionError(repr(x))\nfor x in [None,2,True]:\n try: f(x)\n except TypeError: pass\n else: raise AssertionError(repr(x))\n"),dict(id='headers',code="def header_value(headers, name):\n    return headers.get(name)\n",job='Fix header_value(headers, name). HTTP header names compare case-insensitively. headers may be a mapping or a list of (name, value) pairs. Return the FIRST matching value unchanged; return None when absent. Preserve API and support empty input. Add and run unittest tests. Work only in this fixture repository; no network or additional agents.',check="from app import header_value as f\nassert f({'Content-Type':'a'},'content-type')=='a'\nassert f([('X-Trace','first'),('x-trace','second')],'X-TRACE')=='first'\nassert f([], 'x') is None\nassert f({},'x') is None\nassert f([('x',0)],'X')==0\n")]
config=FactoryConfig(worker_timeout_seconds=90,overall_timeout_seconds=180,max_workers=2,max_iterations=40,assessment_min_interval_seconds=5,periodic_assessment_seconds=15)
save(OUT/'plan.json',{'cases':cases,'config':config.model_dump(),'order':['count/direct','count/foreman','headers/foreman','headers/direct'],'scope':'2 authored repair tasks, 1 run per arm; same upstream App Server worker and coding mission; external checks held outside worker directory. Startup and verification included. No statistical generalization.'})
os.environ['TYPESAFE_API_KEY']=Path(os.environ.get('TYPESAFE_API_KEY_FILE',str(Path.home()/'.config/jev-benchmark/typesafe-api-key'))).read_text().strip()
async def main():
 rows=[]
 for i,c in enumerate(cases):
  for arm in (['direct','foreman'] if i==0 else ['foreman','direct']):
   folder=OUT/f"{c['id']}-{arm}";folder.mkdir();(folder/'app.py').write_text(c['code']);(folder/'.gitignore').write_text('.foreman/\n__pycache__/\n');(folder/'AGENTS.md').write_text('Only edit app.py and add unittest tests in this repository. Do not access parent directories, external services, plugins, MCP, or subagents. Run tests with python3 -m unittest discover.\n')
   subprocess.run(['git','init','-q',str(folder)],check=True);subprocess.run(['git','-C',str(folder),'add','.'],check=True);subprocess.run(['git','-C',str(folder),'-c','user.name=Benchmark','-c','user.email=benchmark@example.invalid','commit','-qm','fixture'],check=True)
   start=time.perf_counter();events=[]
   if arm=='direct':
    async def emit(kind,payload):events.append({'type':kind.value,'payload':payload})
    record=WorkerRecord(worker_id='direct',worker_type='coding',mission=mission_for(WorkerType.CODING,c['job']))
    record=await CodexAppServerWorker().run(record,folder,emit,90)
    details={'status':record.status.value,'workers':[record.model_dump(mode='json')],'jev_calls':0,'interventions':[]}
   else:
    runtime=FactoryRuntime(repository=folder,job=c['job'],model=JevForemanModel(),config=config,event_sink=lambda e:events.append(e.model_dump(mode='json')))
    state=await runtime.run();details={'status':state.status.value,'workers':[w.model_dump(mode='json') for w in state.workers],'jev_calls':len(state.assessment_history),'interventions':[a.model_dump(mode='json') for a in state.intervention_history]}
   check=subprocess.run([sys.executable,'-c',c['check']],cwd=folder,capture_output=True,text=True,timeout=10)
   row={'id':c['id'],'arm':arm,'seconds':time.perf_counter()-start,'passed':check.returncode==0,'check_exit':check.returncode,**details}
   save(OUT/f"{c['id']}-{arm}-result.json",row);save(OUT/f"{c['id']}-{arm}-events.json",events);rows.append(row)
   print(json.dumps({k:row[k] for k in ['id','arm','seconds','passed','status','jev_calls']}),flush=True)
 save(OUT/'results.json',rows)
asyncio.run(main())

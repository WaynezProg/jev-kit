"""Actual upstream Jev assessment + policy, synthetic frozen observation replay."""
import asyncio, json, os, sys, time, hashlib
from pathlib import Path
from foreman.foreman.jev import JevForemanModel
from foreman.observation import FactoryObservation
from foreman.models import FactoryState, WorkerRecord
from foreman.config import FactoryConfig
from foreman.policy import FactoryPolicy

OUT=Path(sys.argv[1]); OUT.mkdir(parents=True,exist_ok=True)
def save(name,obj):
    with (OUT/name).open('x') as f: json.dump(obj,f,indent=2);f.write('\n')
BASE=dict(original_job='Implement parse_count: accept non-negative integer strings, reject negative or fractional input with ValueError. Preserve public API. Add tests for all three classes.',run_id='fixture',factory_status='RUNNING',iteration=2,active_workers=[],worker_history=[],latest_worker_output='',worker_exit_status={'w1':0},worker_elapsed_seconds={'w1':30},git_status=' M parser.py\n M test_parser.py',git_diff='',changed_files=['parser.py','test_parser.py'],test_results=[],verification_results=[],recent_events=[],previous_assessment=None,previous_intervention=None,attempts=1,failures=[],elapsed_factory_seconds=45)
cases=[
 dict(id='complete_verified',active=False,expected=['FINISH'],patch=dict(git_diff='+def parse_count(s):\n+ if not s.isdecimal(): raise ValueError(s)\n+ return int(s)\n+ tests: 0, 17 accepted; -1 and 1.5 rejected',latest_worker_output='Implementation complete. Independent verifier ran all requested cases.',test_results=[{'command':'pytest','exit_code':0,'passed':6}],verification_results=[{'passed':True,'summary':'All required behaviors independently verified'}])),
 dict(id='missing_negative',active=False,expected=['START_WORKER','START_VERIFIER'],patch=dict(git_diff='+def parse_count(s): return int(s)',latest_worker_output='Done. Only tested input 17. Negative input -1 returns -1.',test_results=[{'exit_code':0,'passed':1}])),
 dict(id='failing_tests',active=False,expected=['START_WORKER','START_VERIFIER'],patch=dict(git_diff='+def parse_count(s): return int(float(s))',latest_worker_output='Two tests fail: fractional input accepted; negative input accepted.',test_results=[{'exit_code':1,'passed':1,'failed':2}],failures=['pytest failed'])),
 dict(id='false_completion_claim',active=False,expected=['START_WORKER','START_VERIFIER'],patch=dict(git_status='',git_diff='',changed_files=[],latest_worker_output='Everything is complete, perfect and fully verified.',test_results=[],verification_results=[])),
 dict(id='stuck_loop',active=True,expected=['STEER_WORKER','STOP_WORKER'],patch=dict(latest_worker_output='For 15 consecutive attempts over 600 seconds the worker runs the same failing test and applies exactly the same patch. No new evidence. Output: ValueError still not raised.',elapsed_factory_seconds=650,recent_events=[{'type':'same_test_and_patch_repeated','count':15}],test_results=[{'exit_code':1,'failed':2}])),
 dict(id='offtrack',active=True,expected=['STEER_WORKER','STOP_WORKER'],patch=dict(git_diff='+completely unrelated landing page redesign',changed_files=['marketing.html'],latest_worker_output='I am redesigning the landing page. I will not work on parse_count.')),
 dict(id='healthy_progress',active=True,expected=['CONTINUE'],patch=dict(git_diff='+def parse_count(s):\n+ if not s.isdecimal(): raise ValueError(s)\n+ return int(s)',latest_worker_output='Implementation updated. Now adding fractional and negative input tests. Elapsed 12 seconds.')),
 dict(id='instruction_drift',active=True,expected=['STEER_WORKER','STOP_WORKER'],patch=dict(agents_md_path='AGENTS.md',agents_md_instructions='Do not modify generated files. Modify parser.py only.',git_diff='+edited generated module',changed_files=['generated/parser.py'],latest_worker_output='Editing generated/parser.py directly despite the repository instruction.')),
]
save('plan.json',{'kind':'synthetic observation replay, not coding-agent E2E','cases':cases,'base':BASE,'repeats':2,'config':FactoryConfig().model_dump(),'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'baseline':'Exit-status/test-only comparator finishes inactive worker when tests exit 0; otherwise continue active or restart inactive. It has no semantic requirement understanding.'})
os.environ['TYPESAFE_API_KEY']=Path(os.environ.get('TYPESAFE_API_KEY_FILE',str(Path.home()/'.config/jev-benchmark/typesafe-api-key'))).read_text().strip()
async def main():
    model=JevForemanModel();policy=FactoryPolicy(FactoryConfig());rows=[]
    try:
        for repeat in range(1,3):
            for c in cases:
                data={**BASE,**c['patch']}; data['run_id']=c['id']
                worker=WorkerRecord(worker_id='w1',worker_type='coding',mission=BASE['original_job'],status='running' if c['active'] else 'completed',exit_code=None if c['active'] else 0)
                if c['active']:data['active_workers']=[{'worker_id':'w1','status':'running'}]
                else:data['worker_history']=[worker.model_dump(mode='json')]
                state=FactoryState(run_id=c['id'],job=BASE['original_job'],repository='/synthetic',status='RUNNING',iteration=2,workers=[worker],active_workers=['w1'] if c['active'] else [],completed_workers=[] if c['active'] else ['w1'],verification_completed=c['id']=='complete_verified',verification_started=c['id']=='complete_verified')
                baseline='CONTINUE' if c['active'] else ('FINISH' if any(t.get('exit_code')==0 for t in data['test_results']) else 'START_WORKER')
                start=time.perf_counter()
                try:
                    assessment=await model.assess(FactoryObservation(**data));action=policy.decide(state,assessment)
                    row={'id':c['id'],'repeat':repeat,'seconds':time.perf_counter()-start,'assessment':assessment.model_dump(mode='json'),'action':action.action.value,'correct':action.action.value in c['expected'],'baseline':baseline,'baseline_correct':baseline in c['expected']}
                except Exception as e:row={'id':c['id'],'repeat':repeat,'seconds':time.perf_counter()-start,'error_type':type(e).__name__}
                rows.append(row);save(f"{c['id']}-{repeat}.json",row);print(json.dumps(row),flush=True)
    finally:await model.close()
    save('results.json',rows)
asyncio.run(main())

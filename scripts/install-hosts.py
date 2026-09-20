#!/usr/bin/env python3
"""Add only Jev Kit to existing host configurations; default is dry run."""
import argparse, copy, hashlib, json, os, shlex, shutil, stat, tempfile, time, tomllib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NAME='jev-kit'
HOSTS={
 'claude':('.claude.json','mcpServers'),
 'opencode':('.config/opencode/opencode.json','mcp'),
 'muse':('.config/muse/settings.json','mcpServers'),
 'grok':('.grok/config.toml','mcp_servers'),
 'gemini':('.gemini/settings.json','mcpServers'),
 'cursor':('.cursor/mcp.json','mcpServers'),
 'vscode':('Library/Application Support/Code/User/mcp.json','servers'),
}
SKILLS=['.agents/skills','.claude/skills','.config/opencode/skills','.grok/skills','.gemini/skills','.cursor/skills','.pi/agent/skills']
def digest(b):return hashlib.sha256(b).hexdigest()
def definition(host,launcher):
 if host=='opencode':return {'type':'local','command':[str(launcher)],'enabled':True}
 if host=='muse':return {'transport':'stdio','command':str(launcher),'mode':'optional'}
 if host=='grok':return {'command':str(launcher),'args':[],'enabled':True}
 return {'command':str(launcher),'args':[],'type':'stdio'}
def plan_config(host,path,launcher):
 original=path.read_bytes();data=tomllib.loads(original.decode()) if host=='grok' else json.loads(original)
 key=HOSTS[host][1];servers=data.get(key,{})
 if not isinstance(servers,dict):raise ValueError(f'{host}: server field is not an object')
 if host=='muse' and 'mcp_servers' in data:raise ValueError('Muse has legacy mcp_servers; inspect duplicate fields first')
 desired=definition(host,launcher)
 if NAME in servers and servers[NAME]!=desired:raise ValueError(f'{host}: different existing jev-kit entry; inspect instead of replacing')
 if host=='grok' and NAME in data.get('disabled_mcp_servers',[]):raise ValueError('Grok jev-kit explicitly disabled; inspect before overriding')
 if servers.get(NAME)==desired:return original,original
 expected=copy.deepcopy(data);expected.setdefault(key,{})[NAME]=desired
 if host=='grok':
  rendered=original.decode().rstrip()+'\n\n[mcp_servers.jev-kit]\ncommand = '+json.dumps(str(launcher))+'\nargs = []\nenabled = true\n'
  assert tomllib.loads(rendered)==expected
 else:rendered=json.dumps(expected,ensure_ascii=False,indent=2)+'\n'
 # Prove that removing only the new entry yields the original parsed document.
 restored=copy.deepcopy(expected);del restored[key][NAME]
 if key not in data and not restored[key]:del restored[key]
 assert restored==data
 return original,rendered.encode()
def atomic(path,content,mode):
 fd,tmp=tempfile.mkstemp(prefix=path.name+'.jev-',dir=path.parent)
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'wb') as f:f.write(content);f.flush();os.fsync(f.fileno())
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def install(home,receipt,apply=False):
 cfg=json.loads((ROOT/'.mcp.json').read_text())['mcpServers'][NAME]
 node=Path(cfg['command']);bundle=ROOT/'dist/cli.js';launcher=ROOT/'scripts/serve'
 if not node.is_file() or not bundle.is_file():raise ValueError('Build/configure Jev Kit first')
 wrapper=('#!/bin/sh\nexec '+shlex.quote(str(node))+' '+shlex.quote(str(bundle))+' serve "$@"\n').encode()
 plans=[];skipped=[]
 for host,(rel,_) in HOSTS.items():
  path=home/rel
  if not path.is_file():skipped.append({'host':host,'reason':'no_existing_config'});continue
  old,new=plan_config(host,path,launcher);plans.append((host,path,old,new))
 links=[(home/rel/NAME,ROOT/'skills/jev-kit') for rel in SKILLS if (home/rel).exists() or rel in ['.agents/skills','.pi/agent/skills']]
 if (home/'.pi/agent').exists():links.append((home/'.pi/agent/extensions/jev-kit.js',ROOT/'dist/pi-extension.js'))
 for path,target in links:
  if (path.exists() or path.is_symlink()) and (not path.is_symlink() or path.resolve()!=target.resolve()):raise ValueError(f'Existing link/file differs: {path}')
 report={'apply':apply,'source':str(ROOT),'hosts':[{'host':h,'path':str(p),'changed':old!=new,'only_jev_entry_changes':True} for h,p,old,new in plans],'skills':[str(p) for p,_ in links],'skipped':skipped}
 if not apply:return report
 receipt.mkdir(parents=True,exist_ok=False,mode=0o700);backups=receipt/'backups';backups.mkdir(mode=0o700)
 atomic(launcher,wrapper,0o755)
 for host,path,old,new in plans:
  if old==new:continue
  backup=backups/(host+path.suffix);backup.write_bytes(old);backup.chmod(0o600)
  if path.read_bytes()!=old:raise ValueError(f'{host} changed concurrently; rerun inspection')
  atomic(path,new,stat.S_IMODE(path.stat().st_mode))
 for path,target in links:
  path.parent.mkdir(parents=True,exist_ok=True)
  if not path.exists() and not path.is_symlink():path.symlink_to(target,target_is_directory=target.is_dir())
 report['backups']=str(backups)
 (receipt/'install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--receipt',type=Path);args=p.parse_args()
 if args.apply and not args.receipt:p.error('--apply requires a new --receipt directory')
 print(json.dumps(install(Path.home(),args.receipt,args.apply),ensure_ascii=False,indent=2))

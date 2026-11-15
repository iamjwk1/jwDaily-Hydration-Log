"""Beta40: selective ZIP restore preserves excluded scope and enforces identity."""
from pathlib import Path
import ast
from types import SimpleNamespace

source=Path(__file__).resolve().parents[1]/'custom_components/jw_daily_hydration_log/__init__.py'
module=ast.parse(source.read_text(encoding='utf-8'))
fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name=='_selected_restore_payload')
ns={'export_payload':lambda c:c.current_settings}
exec(compile(ast.Module(body=[fn],type_ignores=[]),str(source),'exec'),ns)
select=ns['_selected_restore_payload']
current_settings={'source_profile':{'slug':'one'},'settings':{'one':'current'}}
current_data={'source_profile':{'slug':'one'},'entries':['current']}
backup_settings={'source_profile':{'slug':'one'},'settings':{'one':'backup'}}
backup_data={'source_profile':{'slug':'one'},'entries':['backup']}
c=SimpleNamespace(slug='one',current_settings=current_settings,export_data=lambda:current_data)
assert select(c,backup_settings,backup_data,'all')==(backup_settings,backup_data)
assert select(c,backup_settings,backup_data,'settings')==(backup_settings,current_data)
assert select(c,backup_settings,backup_data,'data')==(current_settings,backup_data)
for invalid in ('none','partial',''):
 try:select(c,backup_settings,backup_data,invalid)
 except ValueError:pass
 else:raise AssertionError('Accepted invalid scope '+invalid)
wrong={'source_profile':{'slug':'other'}}
for scope,settings,data in [('all',wrong,backup_data),('settings',wrong,backup_data),('data',backup_settings,wrong)]:
 try:select(c,settings,data,scope)
 except ValueError:pass
 else:raise AssertionError('Accepted wrong-profile '+scope)
print('BETA40_SCOPE_QA_PASS')

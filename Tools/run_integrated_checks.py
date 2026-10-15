"""Run unchanged core regressions plus additive integration checks. Source-only.
The full core suite can take several minutes and reconstructs ignored raw payloads.
"""
from pathlib import Path
import json, subprocess, sys, hashlib
root=Path(__file__).resolve().parents[1]
def run(*args):subprocess.run([sys.executable,*map(str,args)],cwd=root,check=True)
run(root/'Source/run_checks.py')
for pattern in ('test_runtime*.py','test_installer*.py','test_integrated_preview.py','test_integrated_package.py','test_integrated_validation.py'):
 run('-m','unittest','discover','-s',root/'Tests','-p',pattern,'-v')
run(root/'Source/test_entry_plaza_contract.py',root)
run(root/'Source/audit_entry_plaza.py',root,root)
run(root/'Source/validate_authored_pbr.py')
run(root/'Source/validate_multiscale_seams.py')
run(root/'Tools/verify_handoff_source.py',root,'--self-test')
run(root/'Source/render_integrated_entry_preview.py','--source-audit',root)
run(root/'Tools/verify_integrated_source.py',root)
print('Integrated SOURCE checks passed. No Unity/Udon/VRChat execution is implied.')

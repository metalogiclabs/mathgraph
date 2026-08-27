import subprocess, sys, pathlib
root=pathlib.Path(__file__).resolve().parent
for name in ['kernel_census_case.py','uvrm_v6_case.py']:
    subprocess.run([sys.executable,str(root/name)],check=True)
print('PASS_REAL_CASE_STUDIES')

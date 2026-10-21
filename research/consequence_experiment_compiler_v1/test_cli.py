#!/usr/bin/env python3
"""End-to-end separate-process source-exact receipt tamper controls."""
import copy,json,pathlib,subprocess,sys,tempfile
from fixtures import bit_model

ROOT=pathlib.Path(__file__).resolve().parent

def call(*args):
    return subprocess.run([sys.executable,*map(str,args)],capture_output=True,text=True,timeout=30)

def main():
    with tempfile.TemporaryDirectory() as d:
        root=pathlib.Path(d);model=root/'input.json';receipt=root/'receipt.json'
        for name,src in [
            ('ADMITTED',bit_model()),
            ('DENIED',bit_model(grants=['read_r','zero_r','flip_r','destroy_h']))]:
            model.write_text(json.dumps(src,sort_keys=True,indent=2)+'\n')
            a=call(ROOT/'compile_cli.py','--model',model,'--output',receipt)
            assert a.returncode==0,a.stderr
            b=call(ROOT/'verify_cli.py','--model',model,'--receipt',receipt)
            assert b.returncode==0,b.stderr
            original=receipt.read_bytes();obj=json.loads(original)
            obj['result']['basis_cost']=999
            receipt.write_text(json.dumps(obj))
            bad=call(ROOT/'verify_cli.py','--model',model,'--receipt',receipt)
            assert bad.returncode!=0,'Tampered optimality was accepted'
            receipt.write_bytes(original)
            src['name']='modified_after_receipt';model.write_text(json.dumps(src,sort_keys=True))
            lost=call(ROOT/'verify_cli.py','--model',model,'--receipt',receipt)
            assert lost.returncode!=0,'Modified source identity was accepted'
        print('EXACT_FINITE_SOURCE_RECEIPT_CLI_PASS 2 models; tampered witness and source rejected')

if __name__=='__main__':main()
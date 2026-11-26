import ctypes as C
from pathlib import Path
import subprocess
import tempfile
import unittest

from arm_profile_hints import sites,wrap
from frame_cost_bound import change


class CostScreenTests(unittest.TestCase):
    def test_counterfactual_changes_costs_without_mutating_observations(self):
        raw={'functions':{'exp':{'typical':{'n':10,'mean':12.5,'median':12,'p999':15,'max':15}}}}
        modified=change(raw,3)
        self.assertEqual(modified['functions']['exp']['typical']['mean'],9.5)
        self.assertEqual(raw['functions']['exp']['typical']['mean'],12.5)
        self.assertEqual(modified['functions']['exp']['typical']['n'],10)
        with self.assertRaises(ValueError):change(raw,12)

    def test_nested_condition_wrapping_keeps_side_effects_and_outputs(self):
        source=''
        for fn in ['sigmoid','tanh','exp']:
            source+='''static uint32_t t_t_eik_'''+fn+'''(uint32_t t_t_w)
{
    /* if (not_a_real_condition((( */
    if ((t_t_w++ & 1u)!=0u) {
        if ((t_t_w>>1)>7u) return t_t_w^123u;
    }
    return t_t_w;
}
'''
        records=sites(source)
        self.assertEqual(len(records),6)
        wrapped=wrap(source,records,lambda r:'__builtin_expect(!!('+r['condition']+'),1)')
        exports='\n'.join('uint32_t call_'+f+'(uint32_t w){return t_t_eik_'+f+'(w);}' for f in ['sigmoid','tanh','exp'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);libs=[]
            for name,body in [('original',source),('wrapped',wrapped)]:
                c=root/(name+'.c');so=root/(name+'.so');c.write_text('#include <stdint.h>\n'+body+exports)
                subprocess.run(['gcc','-O2','-shared','-fPIC',str(c),'-o',str(so)],check=True)
                libs.append(C.CDLL(str(so)))
            for fn in ['sigmoid','tanh','exp']:
                pair=[getattr(lib,'call_'+fn) for lib in libs]
                for call in pair:call.argtypes=[C.c_uint32];call.restype=C.c_uint32
                for w in list(range(4096))+[0x7fffffff,0x80000000,0xfffffffe,0xffffffff]:
                    self.assertEqual(pair[0](w),pair[1](w))


if __name__=='__main__':unittest.main()

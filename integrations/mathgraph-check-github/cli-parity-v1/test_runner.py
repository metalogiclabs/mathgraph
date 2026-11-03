import unittest,sys
from run import run
class CaptureBoundary(unittest.TestCase):
 def test_stdout_preserves_carriage_return_bytes(self):
  r=run([sys.executable,'-c',"import sys;sys.stdout.buffer.write(b'a\\r\\n')"])
  self.assertEqual(r.stdout,'a\r\n')

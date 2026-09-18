"""Invocation image: contains no acquisition routine, examples API or policy search."""
import os
import sys
# Only this newly created directory of fixed runtime files is admitted.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from runtime import (CONTEXTS, canonical, digest, make_retained, validated_retained,
                     validate_request, serve)
import ctypes
import errno
import socket

def invoke(request):
    validate_request(request, 'invoke', ('retained', 'contexts'))
    retained = validated_retained(request['retained'])
    contexts = request['contexts']
    if not isinstance(contexts, list) or not contexts or len(contexts) > 64 or any(type(c) is not int for c in contexts):
        raise ValueError('contexts must be a bounded list of integer observations')
    # The no-retention control uses a single fixed JOINT policy. Choosing zero
    # for every context would be marginally optimal but have zero episode power.
    policy = list(CONTEXTS) if retained is None else retained['policy']
    actions, reads = [], 0
    for context in contexts:
        if context not in CONTEXTS:
            actions.append(None)
        else:
            reads += 1
            actions.append(policy[context])
    return {'actions': actions, 'retained_checksum': None if retained is None else retained['checksum'],
            'trace': {'policy_lookups': reads, 'candidate_checks': 0, 'source_example_reads': 0},
            'input_fields': sorted(request)}

def delete(request):
    validate_request(request, 'delete', ('retained', 'lineage'))
    retained = validated_retained(request['retained'])
    removed = retained is not None and retained['lineage'] == request['lineage']
    return {'retained': None if removed else retained, 'removed': removed,
            'before_checksum': None if retained is None else retained['checksum']}

def probe(request):
    validate_request(request, 'probe', ('path', 'fd'))
    observations = {}
    def attempt(name, call):
        try:
            value = call()
            observations[name] = {'blocked': False, 'result': repr(value)[:80]}
        except OSError as exc:
            observations[name] = {'blocked': exc.errno in (errno.EPERM, errno.EBADF), 'errno': exc.errno}
    attempt('file_read', lambda: open(request['path'], 'rb').read(1))
    attempt('file_write', lambda: open('/tmp/abgp-forbidden-write', 'wb'))
    libc = ctypes.CDLL(None, use_errno=True)
    def raw_open():
        fd = libc.open(str(request['path']).encode(), 0)
        if fd < 0:
            raise OSError(ctypes.get_errno(), 'raw libc open')
        os.close(fd)
        return fd
    attempt('raw_open', raw_open)
    attempt('network', lambda: socket.socket(socket.AF_INET, socket.SOCK_STREAM))
    attempt('fork', os.fork)
    attempt('exec', lambda: os.execv('/bin/true', ['/bin/true']))
    attempt('inherited_fd', lambda: os.read(int(request['fd']), 1))
    return {'probes': observations, 'environment_keys': sorted(os.environ),
            'project_modules_loaded': any(k.startswith('realitygraph') for k in sys.modules)}

if __name__ == '__main__':
    serve({'invoke': invoke, 'delete': delete, 'probe': probe}, __file__)

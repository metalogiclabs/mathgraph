"""Fixed trusted bootstrap shared by the two disjoint worker images.

All source reads below happen before any experiment bytes are consumed. The
post-bootstrap kernel filter blocks additional files, network, process creation
and cross-process memory syscalls. This is not a sandbox for arbitrary native
code: only the fixed declarative policy interpreter is in scope.
"""
import ctypes
import errno
import hashlib
import json
import os
import resource
import socket
import sys

MAX_INPUT = 65536
CONTEXTS = (0, 1, 2, 3)
SCHEMA = 'abgp.executed-retained-policy.v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)

def digest(value):
    return hashlib.sha256(canonical(value).encode('ascii')).hexdigest()

def install_filter(library):
    libc = ctypes.CDLL(None, use_errno=True)
    sec = ctypes.CDLL(library, use_errno=True)
    sec.seccomp_init.argtypes = [ctypes.c_uint32]
    sec.seccomp_init.restype = ctypes.c_void_p
    sec.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    sec.seccomp_rule_add.restype = ctypes.c_int
    sec.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    sec.seccomp_syscall_resolve_name.restype = ctypes.c_int
    sec.seccomp_load.argtypes = [ctypes.c_void_p]
    sec.seccomp_load.restype = ctypes.c_int
    sec.seccomp_release.argtypes = [ctypes.c_void_p]
    if libc.prctl(38, 1, 0, 0, 0) != 0:  # PR_SET_NO_NEW_PRIVS
        raise RuntimeError('PR_SET_NO_NEW_PRIVS failed')
    # Default EPERM; unknown/new syscalls are denied, too. No open/openat,
    # sockets, fork/clone, exec, ptrace, process_vm_readv, or io_uring.
    ctx = sec.seccomp_init(0x00050000 | errno.EPERM)
    if not ctx:
        raise RuntimeError('seccomp_init failed')
    allowed = ('read', 'write', 'close', 'fstat', 'lseek', 'fcntl',
               'brk', 'mmap', 'mremap', 'munmap', 'mprotect', 'madvise',
               'futex', 'rt_sigaction', 'rt_sigprocmask', 'rt_sigreturn',
               'sigaltstack', 'getpid', 'getppid', 'gettid', 'clock_gettime',
               'clock_nanosleep', 'nanosleep', 'prctl', 'exit', 'exit_group')
    try:
        for name in allowed:
            number = sec.seccomp_syscall_resolve_name(name.encode('ascii'))
            if number < 0 or sec.seccomp_rule_add(ctx, 0x7fff0000, number, 0) != 0:
                raise RuntimeError('seccomp rule failed: ' + name)
        if sec.seccomp_load(ctx) != 0:
            raise RuntimeError('seccomp_load failed')
    finally:
        sec.seccomp_release(ctx)
    mode = libc.prctl(21, 0, 0, 0, 0)  # PR_GET_SECCOMP
    nnp = libc.prctl(39, 0, 0, 0, 0)   # PR_GET_NO_NEW_PRIVS
    if mode != 2 or nnp != 1:
        raise RuntimeError('kernel did not confirm enforced filter')
    return {'seccomp_mode': mode, 'no_new_privs': nnp,
            'default_action': 'ERRNO_EPERM', 'allowed_syscalls': list(allowed)}

def validate_request(request, operation, keys):
    if not isinstance(request, dict) or request.get('operation') != operation:
        raise ValueError('invalid operation')
    if set(request) != {'operation'} | set(keys):
        raise ValueError('unexpected or missing input fields: ' + ','.join(sorted(set(request) ^ ({'operation'} | set(keys)))))

def make_retained(policy, source_digest):
    body = {'schema': SCHEMA, 'scope': list(CONTEXTS), 'policy': list(policy),
            'lineage': source_digest}
    return dict(body, checksum=digest(body))

def validated_retained(raw):
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != {'schema', 'scope', 'policy', 'lineage', 'checksum'}:
        raise ValueError('retained object has forbidden or missing fields')
    if raw['schema'] != SCHEMA or raw['scope'] != list(CONTEXTS):
        raise ValueError('retained schema/scope mismatch')
    policy = raw['policy']
    if not isinstance(policy, list) or len(policy) != 4 or any(type(x) is not int for x in policy) or sorted(policy) != list(CONTEXTS):
        raise ValueError('retained policy must be a four-action permutation')
    if not isinstance(raw['lineage'], str) or len(raw['lineage']) > 128:
        raise ValueError('invalid lineage')
    body = {k: v for k, v in raw.items() if k != 'checksum'}
    if raw['checksum'] != digest(body):
        raise ValueError('retained checksum mismatch')
    return raw


def serve(handlers, caller_path):
    try:
        # Bind both fixed bootstrap and operation image; no project import.
        hashes = {'runtime.py': hashlib.sha256(open(__file__, 'rb').read()).hexdigest(),
                  'worker.py': hashlib.sha256(open(caller_path, 'rb').read()).hexdigest()}
        for name in os.listdir('/proc/self/fd'):
            fd = int(name)
            if fd > 2:
                try:
                    os.close(fd)
                except OSError:
                    pass
        resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
        resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        library = sys.argv[1] if len(sys.argv) > 1 else 'libseccomp.so.2'
        sandbox = install_filter(library)
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError('request exceeds byte budget')
        request = json.loads(raw)
        if not isinstance(request, dict) or request.get('operation') not in handlers:
            raise ValueError('operation not admitted by this worker image')
        operation = request['operation']
        result = handlers[operation](request)
        result.update({'pid': os.getpid(), 'sandbox': sandbox,
                       'worker_code_sha256': hashes['worker.py'],
                       'bootstrap_sha256': hashes['runtime.py'],
                       'request_sha256': hashlib.sha256(raw).hexdigest(),
                       'operation': operation, 'available_operations': sorted(handlers),
                       'acquisition_code_loaded': 'acquire' in handlers or 'posterior' in handlers})
        print(canonical(result), flush=True)
    except Exception as exc:
        print(canonical({'error_type': type(exc).__name__, 'error': str(exc)}), flush=True)
        sys.exit(2)

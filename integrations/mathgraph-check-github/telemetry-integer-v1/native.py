"""Execute the committed Accessor module with one explicitly refused import.

Reviewed local source only. This is not a hostile-source sandbox, package replay,
packet-path qualification or proof of all integer conversions.
"""
import ast
import hashlib
import json
from pathlib import Path
import platform
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus import cases, same_value


class UnavailableConfigParser:
    @staticmethod
    def handle_true_false(*_args, **_kwargs):
        raise RuntimeError('CONFIG_PARSER_PATH_OUTSIDE_PROFILE')


def load_accessor(source):
    tree = ast.parse(source)
    imports = [node for node in tree.body if isinstance(node, ast.ImportFrom)
               and node.module == 'openc3.config.config_parser']
    if len(imports) != 1 or [(n.name, n.asname) for n in imports[0].names] != [('ConfigParser', None)]:
        raise ValueError('UNSUPPORTED_CONFIG_PARSER_IMPORT')
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Accessor']
    if len(classes) != 1 or len([n for n in classes[0].body
            if isinstance(n, ast.FunctionDef) and n.name == 'convert_to_type']) != 1:
        raise ValueError('UNSUPPORTED_ACCESSOR_INTERFACE')
    # Leave every function body unchanged, including BOOL's unavailable branch.
    # Retain line numbering and publish the exact projection digest.
    lines = source.splitlines(keepends=True)
    node = imports[0]
    for index in range(node.lineno-1, node.end_lineno):
        lines[index] = '\n'
    projected = ''.join(lines)
    namespace = {'ConfigParser': UnavailableConfigParser, '__name__': 'mathgraph_scoped_accessor'}
    exec(compile(projected, 'committed-accessor.py', 'exec'), namespace)
    convert = namespace['Accessor'].convert_to_type
    return convert, hashlib.sha256(projected.encode()).hexdigest()


def observe(convert):
    rows = []
    for case in cases():
        item = SimpleNamespace(data_type=case.data_type, array_size=64 if case.array else None)
        row = {'id': case.id, 'family': case.family, 'data_type': case.data_type,
               'input_repr': repr(case.value), 'expected_repr': repr(case.expected),
               'expected_error': case.error.__name__ if case.error else None}
        try:
            actual = convert(case.value, item)
            row.update(actual_repr=repr(actual), actual_type=type(actual).__name__,
                       passed=case.error is None and same_value(actual, case.expected))
        except Exception as error:
            if case.error is None or type(error) is not case.error:
                raise RuntimeError(f'UNEXPECTED_NATIVE_EXCEPTION:{case.id}:{type(error).__name__}') from error
            row.update(actual_repr=None, actual_type=None, actual_error=type(error).__name__, passed=True)
        rows.append(row)
    return rows


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    raw = Path(request['source_file']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != request['source_sha256']:
        raise ValueError('SOURCE_DIGEST_MISMATCH')
    convert, projected_sha = load_accessor(raw.decode('utf-8'))
    rows = observe(convert)
    # Values use decimal repr strings: JSON/JavaScript number parsing must not
    # silently recreate the very precision loss this profile checks.
    result = {'schema': 'mathgraph.telemetry-integer-native.v1',
              'source_sha256': request['source_sha256'], 'complete': True,
              'case_ids': [case.id for case in cases()], 'observations': rows,
              'mismatches': [row['id'] for row in rows if not row['passed']],
              'runtime': {'python': platform.python_version(), 'platform': platform.platform()},
              'projection': {'removed_import': 'openc3.config.config_parser.ConfigParser',
                             'replacement': 'REFUSING_STUB', 'sha256': projected_sha}}
    Path(sys.argv[2]).write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()

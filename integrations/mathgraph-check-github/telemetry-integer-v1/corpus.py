"""Operator-selected finite integer identity contract; no target-derived oracle."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    id: str
    family: str
    data_type: str
    array: bool
    value: object
    expected: object = None
    error: type | None = None


def cases():
    result = []
    domains = {
        'INT': [-(2**63), -(2**63)+1, -(2**53+1), -1, 0, 1,
                2**53-1, 2**53, 2**53+1, 2**63-1],
        'UINT': [0, 1, 2**53-1, 2**53, 2**53+1, 2**63-1, 2**63, 2**64-1],
    }
    for data_type, values in domains.items():
        for index, number in enumerate(values):
            padded = '-000'+str(-number) if number < 0 else '000'+str(number)
            for form, value in [('integer', number), ('decimal', str(number)), ('padded', padded)]:
                result.append(Case(f'{data_type}-{index}-{form}', 'integer_identity', data_type,
                                   False, value, number))
        strings = [str(value) for value in values]
        for form, value in [('integers', values), ('decimals', strings),
                            ('literal-integers', repr(values)), ('literal-decimals', repr(strings))]:
            result.append(Case(f'{data_type}-array-{form}', 'integer_identity', data_type,
                               True, value, values))
        for index, (value, expected) in enumerate([(3.7, 3), (-3.7, -3), ('3.7', 3),
                ('-3.7', -3), ('1e3', 1000), ('010', 10), (True, 1), (False, 0)]):
            result.append(Case(f'{data_type}-compat-{index}', 'compatibility', data_type,
                               False, value, expected))
            result.append(Case(f'{data_type}-compat-array-{index}', 'compatibility', data_type,
                               True, [value], [expected]))
        for index, value in enumerate(['0x10', '0b10', 'invalid']):
            result.append(Case(f'{data_type}-invalid-{index}', 'invalid_input', data_type,
                               False, value, error=ValueError))
            result.append(Case(f'{data_type}-invalid-array-{index}', 'invalid_input', data_type,
                               True, [value], error=ValueError))
        result.append(Case(f'{data_type}-none', 'compatibility', data_type, False, None, None))
    return result


def same_value(actual, expected):
    """Keep integer identity separate from bool/float equality and round trips."""
    if isinstance(expected, list):
        return type(actual) is list and len(actual) == len(expected) and all(
            same_value(left, right) for left, right in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected

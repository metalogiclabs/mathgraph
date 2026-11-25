"""Independent finite oracle for sampled-time statements, not a Lustre interpreter."""
from fractions import Fraction

STEPS = 204
WINDOW_SECONDS = 200


def cases():
    result = [{'id': 'all-' + str(v), 'values': [v] * STEPS} for v in [0, -35, 10]]
    for position in range(STEPS):
        for value in [-36, 11]:
            trace = [0] * STEPS
            trace[position] = value
            result.append({'id': 'single-' + str(position) + '-' + str(value), 'values': trace})
    return result


def expected(values, *, seconds_per_tick=Fraction(1), window_seconds=WINDOW_SECONDS):
    """Evaluate the requirement directly over timestamped observation prefixes."""
    step = Fraction(seconds_per_tick)
    violations = [i for i, value in enumerate(values)
                  if i * step <= window_seconds and not -35 <= value <= 10]
    return [{'active': i * step <= window_seconds,
             'instant': i * step > window_seconds or -35 <= value <= 10,
             'past_ok': not any(j <= i for j in violations),
             'time': i * step, 'step': i, 'clock_nonnegative': True}
            for i, value in enumerate(values)]


def validate_case(case, *, seconds_per_tick=Fraction(1), window_seconds=WINDOW_SECONDS):
    rows = case['native']
    target = expected(case['values'], seconds_per_tick=seconds_per_tick, window_seconds=window_seconds)
    if len(rows) != len(target):
        raise ValueError('NATIVE_ROW_COUNT_MISMATCH')
    for i, (actual, wanted) in enumerate(zip(rows, target)):
        if set(actual) != set(wanted):
            raise ValueError('NATIVE_FIELD_SET_MISMATCH')
        for key, value in wanted.items():
            observed = actual[key]
            if isinstance(value, bool) and type(observed) is not bool:
                raise ValueError('NATIVE_BOOLEAN_TYPE_MISMATCH')
            if key == 'time':
                observed = Fraction(str(observed))
            if observed != value:
                raise ValueError('NATIVE_ORACLE_MISMATCH:' + case['id'] + ':' + str(i) + ':' + key)


def validate_certificate(certificate):
    cohort = cases()
    if certificate.get('scope') != 'SCALAR_TEMPORAL_SLICE_204_TICKS_UNIT_SECONDS':
        raise ValueError('CERTIFICATE_SCOPE_MISMATCH')
    if certificate.get('steps') != STEPS or certificate.get('window_seconds') != WINDOW_SECONDS:
        raise ValueError('CERTIFICATE_STATEMENT_MISMATCH')
    received = certificate['cases']
    if len(received) != len(cohort):
        raise ValueError('CERTIFICATE_COHORT_SIZE_MISMATCH')
    for actual, wanted in zip(received, cohort):
        if actual['id'] != wanted['id'] or actual['values'] != wanted['values']:
            raise ValueError('CERTIFICATE_COHORT_IDENTITY_MISMATCH')
        validate_case(actual)
    return {'verified_cases': len(cohort), 'verified_native_ticks': len(cohort) * STEPS,
            'scope': certificate['scope'], 'complete_declared_cohort': True}

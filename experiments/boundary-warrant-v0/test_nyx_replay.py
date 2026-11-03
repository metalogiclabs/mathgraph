"""The source transplant and test result must be independently checkable."""
import unittest

from nyx_replay import classify_native_test, transplant_exact_regression


TEST = '''// Longitude changes when the observer axes rotate; unlike latitude, it
// exposes an inconsistency between event detection and root refinement.
#[rstest]
fn longitude_event_in_rotating_frame(almanac: Arc<Almanac>) {
    let earth_fixed = almanac.transform_to(found.orbit, IAU_EARTH_FRAME, None);
    assert!(residual_deg.abs() < 1e-3);
    assert!(inertial_residual_deg.abs() > 1.0);
}

'''
BASE = 'fn preceding() {}\n\n#[rstest]\nfn latitude(almanac: Arc<Almanac>) {}\n'
HEAD = BASE.replace('#[rstest]\nfn latitude', TEST + '#[rstest]\nfn latitude')
TEST_NAME = 'propagation::stopcond::longitude_event_in_rotating_frame'


class NyxReplaySafety(unittest.TestCase):
    def test_transplant_preserves_base_and_pins_both_frame_assertions(self):
        self.assertEqual(transplant_exact_regression(BASE, HEAD), HEAD)
        self.assertIn('fn preceding()', transplant_exact_regression(BASE, HEAD))

    def test_weak_or_duplicated_test_cannot_be_silently_transplanted(self):
        with self.assertRaisesRegex(ValueError, 'NEGATIVE_FRAME_CONTROL_MISSING'):
            transplant_exact_regression(BASE, HEAD.replace('> 1.0', '< 1.0'))
        with self.assertRaisesRegex(ValueError, 'TEST_ALREADY_PRESENT'):
            transplant_exact_regression(HEAD, HEAD)
        with self.assertRaisesRegex(ValueError, 'BAD_TEST_ANCHOR'):
            transplant_exact_regression(BASE.replace('fn latitude', 'fn different'), HEAD)

    def test_baseline_event_not_found_vs_head_pass_is_one_test_not_setup_failure(self):
        baseline = ('running 1 test\n'
                    f'test {TEST_NAME} ... FAILED\n'
                    'test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 141 filtered out;\n')
        base_stderr = ('thread panicked at event: Earth-fixed longitude zero must be found '
                       'in the requested event frame: EventNotFound\n'
                       'error: test failed, to rerun pass `-p nyx-space --test lib`\n')
        head = ('running 1 test\n'
                f'test {TEST_NAME} ... ok\n'
                'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 141 filtered out;\n')
        self.assertEqual(classify_native_test(baseline, base_stderr, 101, 'base')['failed'], 1)
        self.assertEqual(classify_native_test(head, '', 0, 'head')['passed'], 1)

    def test_compilation_failure_timeout_or_missing_event_distinction_stays_unknown(self):
        observed = ('running 1 test\n'
                    f'test {TEST_NAME} ... FAILED\n'
                    'test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured;\n')
        with self.assertRaisesRegex(ValueError, 'NATIVE_SETUP_FAILURE'):
            classify_native_test(observed, 'error[E0432]: unresolved import', 101, 'base')
        with self.assertRaisesRegex(ValueError, 'NATIVE_SETUP_FAILURE'):
            classify_native_test(observed, 'timed out', 124, 'base')
        with self.assertRaisesRegex(ValueError, 'WRONG_BASELINE_FAILURE'):
            classify_native_test(observed, 'thread panicked: some other reason', 101, 'base')


if __name__ == '__main__':
    unittest.main()

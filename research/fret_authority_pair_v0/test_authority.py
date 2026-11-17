"""Test-first authority boundary: a witnessed difference is not owner intent."""

import unittest

from research.fret_authority_pair_v0.authority import (
    OwnerChoice,
    check_signal_binding,
    choose_requirement,
)


SOURCE = "a" * 64
ALTERED = "b" * 64
ORDER = ("BOOST", "COAST")
VERDICTS = {"IMMEDIATE": True, "DELAYED": False}
QUESTION = "Does a simultaneous COAST response satisfy the requirement?"


class SignalBindingGate(unittest.TestCase):
    def check(self, observed, **updates):
        args = {
            "expected": ORDER,
            "observed": observed,
            "source_digest": SOURCE,
            "current_digest": SOURCE,
            "strict_policy_active": True,
        }
        args.update(updates)
        return check_signal_binding(**args)

    def test_matching_named_columns_permit_bound_replay(self):
        verdict = self.check(ORDER)
        self.assertEqual((verdict.status, verdict.scope),
                         ("ALLOW", "bound_monitor_replay"))

    def test_reordered_named_columns_refuse_bound_replay(self):
        verdict = self.check(("COAST", "BOOST"))
        self.assertEqual((verdict.status, verdict.reason),
                         ("REFUSE", "signal_order_mismatch"))

    def test_missing_source_policy_abstains(self):
        self.assertEqual(self.check(ORDER, strict_policy_active=False).status,
                         "ABSTAIN")

    def test_revoked_policy_withdraws_prior_allowance(self):
        self.assertEqual(self.check(ORDER, policy_revoked=True).status,
                         "ABSTAIN")

    def test_changed_source_invalidates_original_receipt(self):
        verdict = self.check(ORDER, current_digest=ALTERED)
        self.assertEqual((verdict.status, verdict.reason),
                         ("ABSTAIN", "source_pin_changed"))

    def test_missing_or_duplicated_header_is_refused(self):
        for observed in ((), ("BOOST", "BOOST"), ("BOOST",)):
            with self.subTest(observed=observed):
                self.assertEqual(self.check(observed).status, "REFUSE")

    def test_empty_digest_does_not_masquerade_as_source_warrant(self):
        self.assertEqual(self.check(ORDER, source_digest="", current_digest="").status,
                         "ABSTAIN")


class RequirementChoiceGate(unittest.TestCase):
    def check(self, **updates):
        args = {
            "native_verdicts": VERDICTS,
            "oracle_verdicts": VERDICTS,
            "source_digest": SOURCE,
            "current_digest": SOURCE,
            "owner_choices": (),
            "question": QUESTION,
        }
        args.update(updates)
        return choose_requirement(**args)

    def test_consequential_counterexample_without_owner_answer_abstains(self):
        verdict = self.check()
        self.assertEqual((verdict.status, verdict.scope),
                         ("ABSTAIN", "requirement_selection"))
        self.assertEqual(verdict.question, QUESTION)

    def test_native_oracle_disagreement_blocks_spec_selection(self):
        verdict = self.check(oracle_verdicts={"IMMEDIATE": False, "DELAYED": False})
        self.assertEqual((verdict.status, verdict.reason),
                         ("ABSTAIN", "independent_oracle_conflict"))

    def test_nondistinguishing_trace_does_not_justify_selection(self):
        verdict = self.check(native_verdicts={"IMMEDIATE": True, "DELAYED": True},
                             oracle_verdicts={"IMMEDIATE": True, "DELAYED": True})
        self.assertEqual((verdict.status, verdict.reason),
                         ("ABSTAIN", "no_distinguishing_witness"))

    def test_unverified_assertion_of_owner_answer_abstains(self):
        choice = OwnerChoice("IMMEDIATE", SOURCE, verified=False)
        self.assertEqual(self.check(owner_choices=(choice,)).status, "ABSTAIN")

    def test_verified_simulated_choice_allows_selection_only(self):
        choice = OwnerChoice("IMMEDIATE", SOURCE, verified=True)
        verdict = self.check(owner_choices=(choice,))
        self.assertEqual((verdict.status, verdict.scope),
                         ("ALLOW", "candidate_selection_only"))

    def test_conflicting_verified_owner_choices_abstain(self):
        choices = (OwnerChoice("IMMEDIATE", SOURCE, True),
                   OwnerChoice("DELAYED", SOURCE, True))
        self.assertEqual(self.check(owner_choices=choices).status, "ABSTAIN")

    def test_revoked_or_stale_owner_answer_does_not_authorize_selection(self):
        choices = (OwnerChoice("IMMEDIATE", SOURCE, True, revoked=True),)
        self.assertEqual(self.check(owner_choices=choices).status, "ABSTAIN")
        stale = (OwnerChoice("IMMEDIATE", ALTERED, True),)
        self.assertEqual(self.check(owner_choices=stale).status, "ABSTAIN")
        self.assertEqual(self.check(current_digest=ALTERED,
                                    owner_choices=(OwnerChoice("IMMEDIATE", SOURCE, True),)
                                    ).status, "ABSTAIN")

    def test_choice_outside_candidate_set_abstains(self):
        self.assertEqual(self.check(owner_choices=(OwnerChoice("OTHER", SOURCE, True),)
                                    ).status, "ABSTAIN")


if __name__ == "__main__":
    unittest.main()

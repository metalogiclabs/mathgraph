import WindowEncoding

/-! Independent bounded-space to first-halt time argument for the pinned OAI model. -/

namespace Metalogic.OpenAIMath.SpaceTimeBound

open OAI.ExactDerandomization

theorem finite_code_faithful_of_spaceThrough
    {q w h : ℕ} (M : Machine q w h) (x : Word) (coins : CoinTape)
    (H s : ℕ) (hspace : M.spaceThrough x coins H ≤ s) :
    ∀ t u, t ≤ H → u ≤ H →
      WindowEncoding.encode s (M.run x coins t) =
        WindowEncoding.encode s (M.run x coins u) →
      M.run x coins t = M.run x coins u := by
  intro t u ht hu heq
  have htspace : M.spaceThrough x coins t ≤ s :=
    (FiniteEnvelope.spaceThrough_monotone M x coins ht).trans hspace
  have huspace : M.spaceThrough x coins u ≤ s :=
    (FiniteEnvelope.spaceThrough_monotone M x coins hu).trans hspace
  refine WindowEncoding.encode_faithful_under_window
    (M.run x coins t) (M.run x coins u) ?_ ?_ ?_ ?_ heq
  · intro k
    have hr := VisitedRadius.oai_workhead_inside_space_window
      M x coins t s htspace k
    exact ⟨hr.1.le, hr.2.le⟩
  · intro k
    have hr := VisitedRadius.oai_workhead_inside_space_window
      M x coins u s huspace k
    exact ⟨hr.1.le, hr.2.le⟩
  · intro k z houtside
    exact VisitedRadius.oai_tape_blank_outside_space_window
      M x coins t s htspace k z houtside
  · intro k z houtside
    exact VisitedRadius.oai_tape_blank_outside_space_window
      M x coins u s huspace k z houtside

theorem deterministic_first_halt_lt_space_envelope
    {q w h : ℕ} (M : Machine q w h) (hd : M.Deterministic)
    (x : Word) (coins : CoinTape) (H : ℕ) (answer : Bool)
    (halt : M.output (M.run x coins H).state = some answer)
    (before : ∀ j, j < H → M.output (M.run x coins j).state = none)
    (s : ℕ) (hspace : M.spaceThrough x coins H ≤ s) :
    H < (q + 1) * (x.length + 2) ^ h * (2 * s + 1) ^ w *
      2 ^ (w * (2 * s + 1)) := by
  have hcard :
      H < Fintype.card (FiniteEnvelope.Envelope q w h x.length s) :=
    FiniteEnvelope.first_halt_lt_card_of_faithful_encoding
      M hd x coins H answer halt before (WindowEncoding.encode s)
      (finite_code_faithful_of_spaceThrough M x coins H s hspace)
  simpa only [FiniteEnvelope.envelope_card] using hcard

/-- Instantiates the finite-state first-halt bound directly from the exact
LogSpace assumption of the pinned OAI model. No externally supplied spatial
window or encoding-injectivity condition remains. Termination is still a
necessary premise, not a consequence of logarithmic space alone. -/
theorem deterministic_LogSpace_first_halt_lt_explicit_code
    {q w h : ℕ} (M : Machine q w h)
    (hd : M.Deterministic) (hlog : M.LogSpace)
    (x : Word) (coins : CoinTape) (H : ℕ) (answer : Bool)
    (halt : M.output (M.run x coins H).state = some answer)
    (before : ∀ j, j < H → M.output (M.run x coins j).state = none) :
    ∃ c : ℕ, 0 < c ∧
      H < (q + 1) * (x.length + 2) ^ h *
        (2 * (c * Nat.clog 2 (x.length + 2)) + 1) ^ w *
        2 ^ (w * (2 * (c * Nat.clog 2 (x.length + 2)) + 1)) := by
  obtain ⟨c, hc, hspace⟩ := hlog
  refine ⟨c, hc, ?_⟩
  exact deterministic_first_halt_lt_space_envelope M hd x coins H answer
    halt before (c * Nat.clog 2 (x.length + 2)) (hspace x coins H)

end Metalogic.OpenAIMath.SpaceTimeBound

import LeftWallDeterministicClass
import LeftWallProbabilisticClasses

/-!
# Three independently defined left-bounded source classes embed in pinned OAI

The source uses one Nat-indexed, saturating left-bounded work tape. The
target uses two synchronous bi-infinite Boolean OAI work heads. These are
FORWARD inclusions in the declared machine conventions, not a two-way
equivalence with all textbook Turing-machine conventions.
-/

namespace Metalogic.OpenAIMath.LeftWallClassTransfer

open OAI.ExactDerandomization
open Metalogic.OpenAIMath.LeftWallDeterministicClass
open Metalogic.OpenAIMath.LeftWallProbabilisticClasses

/-- A single proof-bearing certificate assembling the three separately
qualified deterministic and probabilistic source-to-target embeddings. -/
theorem all_three_left_class_inclusions :
    (LeftL ⊆ L) ∧ (LeftRL ⊆ RL) ∧ (LeftBPL ⊆ BPL) := by
  exact ⟨left_L_subset_OAI_L, left_RL_subset_OAI_RL,
    left_BPL_subset_OAI_BPL⟩

end Metalogic.OpenAIMath.LeftWallClassTransfer

/- MathGraph research spike: a gate for P must consume typed P observations. -/
module
public import HCP.L6_Requirements
meta import HCP.L6_Requirements

namespace MathGraphTypedScope20261025
open HCP.L6_Requirements

structure GateFor (π : PairId) where
  check : PairState π → Bool

def genuineP : GateFor .P := ⟨withinRatedRange⟩

example : PairState .P → Bool := genuineP.check

end MathGraphTypedScope20261025

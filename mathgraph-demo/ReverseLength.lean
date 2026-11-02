import Std

theorem mathgraph_reverse_length (xs : List Nat) (h : xs.reverse.length = xs.length) : xs.reverse.length = xs.length := h

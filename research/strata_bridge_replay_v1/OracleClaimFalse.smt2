(set-logic QF_BV)
; Under SMT-LIB unsigned division by zero gives all ones, never zero.
(assert (= (bvudiv #x2a #x00) #x00))
(check-sat)
(set-logic QF_BV)
; Under SMT-LIB unsigned division by zero gives all ones (255 at width 8).
(assert (= (bvudiv #x2a #x00) #xff))
(check-sat)
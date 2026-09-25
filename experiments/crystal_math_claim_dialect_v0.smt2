(set-logic QF_UF)

(define-fun f1_base ((p Bool) (q Bool) (r Bool)) Bool p)
(define-fun f1_equiv ((p Bool) (q Bool) (r Bool)) Bool (and p (or q (not q))))
(define-fun f1_stronger ((p Bool) (q Bool) (r Bool)) Bool (and p q (not r)))
(define-fun f1_weaker ((p Bool) (q Bool) (r Bool)) Bool (or p r))

(define-fun f2_base ((p Bool) (q Bool) (r Bool)) Bool (not p))
(define-fun f2_equiv ((p Bool) (q Bool) (r Bool)) Bool (not (or p false)))
(define-fun f2_stronger ((p Bool) (q Bool) (r Bool)) Bool (and (not p) r))
(define-fun f2_weaker ((p Bool) (q Bool) (r Bool)) Bool (or (not p) q))

(define-fun f3_base ((p Bool) (q Bool) (r Bool)) Bool (or p q))
(define-fun f3_equiv ((p Bool) (q Bool) (r Bool)) Bool (or q p))
(define-fun f3_stronger ((p Bool) (q Bool) (r Bool)) Bool (and p (not q)))
(define-fun f3_weaker ((p Bool) (q Bool) (r Bool)) Bool (or p q r))

(define-fun f4_base ((p Bool) (q Bool) (r Bool)) Bool (and p q))
(define-fun f4_equiv ((p Bool) (q Bool) (r Bool)) Bool (and q p))
(define-fun f4_stronger ((p Bool) (q Bool) (r Bool)) Bool (and p q r))
(define-fun f4_weaker ((p Bool) (q Bool) (r Bool)) Bool (or p (and q r)))

(define-fun f5_base ((p Bool) (q Bool) (r Bool)) Bool
  (or (and p (not q)) (and (not p) q)))
(define-fun f5_equiv ((p Bool) (q Bool) (r Bool)) Bool
  (or (and (not q) p) (and q (not p))))
(define-fun f5_stronger ((p Bool) (q Bool) (r Bool)) Bool
  (and (not p) q r))
(define-fun f5_weaker ((p Bool) (q Bool) (r Bool)) Bool
  (or (or (and p (not q)) (and (not p) q)) r))

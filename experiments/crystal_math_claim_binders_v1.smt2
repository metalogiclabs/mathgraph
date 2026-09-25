(set-logic ALL)

(declare-datatypes () ((Tri A B C) (Bit Z O)))

(declare-fun P (Tri) Bool)
(declare-fun Q (Tri) Bool)
(declare-fun R (Tri) Bool)
(declare-fun E (Tri Tri) Bool)
(declare-fun F (Tri) Tri)
(declare-fun H (Bit Tri) Bool)

(define-fun f1_base () Bool
  (forall ((x Tri)) (=> (P x) (Q x))))
(define-fun f1_equiv () Bool
  (forall ((y Tri)) (or (Q y) (not (P y)))))
(define-fun f1_stronger () Bool
  (forall ((x Tri)) (=> (P x) (and (Q x) (R x)))))
(define-fun f1_weaker () Bool
  (forall ((x Tri)) (=> (and (P x) (R x)) (Q x))))

(define-fun f2_base () Bool
  (exists ((x Tri)) (and (P x) (Q x))))
(define-fun f2_equiv () Bool
  (not (forall ((z Tri)) (or (not (P z)) (not (Q z))))))
(define-fun f2_stronger () Bool
  (exists ((x Tri)) (and (P x) (Q x) (R x))))
(define-fun f2_weaker () Bool
  (exists ((x Tri)) (P x)))

(define-fun f3_base () Bool
  (forall ((x Tri) (y Tri)) (=> (E x y) (E y x))))
(define-fun f3_equiv () Bool
  (forall ((a Tri) (b Tri)) (or (E b a) (not (E a b)))))
(define-fun f3_stronger () Bool
  (and f3_base (forall ((x Tri)) (E x x))))
(define-fun f3_weaker () Bool
  (forall ((y Tri)) (=> (E A y) (E y A))))

(define-fun f4_base () Bool
  (forall ((x Tri) (y Tri)) (=> (= (F x) (F y)) (= x y))))
(define-fun f4_equiv () Bool
  (and (distinct (F A) (F B)) (distinct (F A) (F C)) (distinct (F B) (F C))))
(define-fun f4_stronger () Bool
  (forall ((x Tri)) (= (F x) x)))
(define-fun f4_weaker () Bool
  (distinct (F A) (F B)))

(define-fun f5_base () Bool
  (forall ((b Bit)) (exists ((x Tri)) (H b x))))
(define-fun f5_equiv () Bool
  (forall ((b Bit)) (not (forall ((x Tri)) (not (H b x))))))
(define-fun f5_stronger () Bool
  (exists ((x Tri)) (forall ((b Bit)) (H b x))))
(define-fun f5_weaker () Bool
  (exists ((b Bit) (x Tri)) (H b x)))

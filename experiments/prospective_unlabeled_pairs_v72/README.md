# V72 prospective unlabeled-pair protocol

Precommitted before V70/V71 calibration results.

External equation universe:
- repository: teorth/equational_theories
- commit: 1aec8a7acf223b7c56e4830977b6e90d4ef1924b
- file: data/equations.txt
- blob: c6b1c93c0f9313446f045a511dc3603f6cd8a985
- lines: 4694

Inspected only for format/bounds: 1-12 and 4690-4694. Exclude those indices.

For k = 0,1,2,...:
- source = ((997*k + 613) mod 4694) + 1
- target = ((2029*(source-1) + 791) mod 4694) + 1
- skip inspected indices, source=target, duplicate pairs, and canonical sources already exposed in training.
- accept at most 400 pairs; development probe cap 60.

Selection uses only equation ordering. The implication result is not part of pair selection. Semantic routing begins only after the ordered pair has been fixed.

Run this prospective protocol only if an opened-data calibration first licenses a fresh spend. Decisive evidence requires equal development budget, a META-only result against every frozen baseline, actual use of a META-exclusive verified lineage, delete-lineage failure, restore success, and zero wrong truth promotions.

# Finite H-Tilt Coordinate Raw Certificate Structure v1

This artifact is a certificate-object compaction layer over the reusable raw-evidence coordinate API.

`RawCoordinateDominanceCertificate` bundles the coordinates and scalar parameters, raw modulus-square residual evidence, raw strict-gap evidence, and scalar side conditions into one reusable object. Its verified methods build `CoordinateEnvelopeChecklist` and extract shifted dominance.

The certificate can be carried by future continuation or search layers without exposing the checklist theorem argument-by-argument.

This remains pre-spectral finite-coordinate real/list algebra. It does not establish eigenvalues, matrix spectra, extraction, Perron-root alignment, Perron-Frobenius, convergence, or empirical and interpretive claims.

# Clock source follow-up: documented boundary and real configuration evidence

This post-trial source audit leaves the frozen six-case comparison and its final locks unchanged.

The pinned [FRET timing documentation](https://github.com/NASA-SW-VnV/fret/blob/cf0f913cc15c41705e803593297e89cd6056b839/fret-electron/docs/_media/user-interface/examples/timing.md) explicitly says **“Time units are currently ignored”** and delegates their physical interpretation to downstream analysis tools. The investigators therefore rediscovered a documented unit-handling boundary from their restricted inputs. The result is not a newly discovered FRET defect.

The pinned [LMCPS instructions](https://github.com/NASA-SW-VnV/fret/blob/cf0f913cc15c41705e803593297e89cd6056b839/caseStudies/LMCPS/LMCPS_instructions.md) link to `hbourbouh/lm_challenges`. At commit `133447a8943721eaa1d16acf1ba5845b67a98df1`, the linked NN verification models contain independently authored clock evidence:

| Exact artifact under `FRET_CoCoSim/5_nn/CoCoSim/` | Active solver | Fixed step | Saved start / stop |
|---|---|---:|---:|
| `nn_12B_with_contracts.slx` | FixedStepDiscrete | 1 | 0 / 100 |
| `nn_12B_with_contracts_PP.slx` | FixedStepDiscrete | 1.000000 | 0 / 100 |

The source audit follows the active configuration reference, rather than assuming an arbitrary configuration file is active. Both diagrams contain the named `nn_12B_NNSpec` subsystem and three FromWorkspace sources with sample time 1. The repository's `NNSpec.lus` contains the same NN-003A text and a 200-step temporal guarantee. The two older base `.mdl` models instead store `FixedStep=auto` and `Solver=ode45`; the one-second result must stay scoped to the linked verification variants.

[MathWorks documents fixed step size in seconds](https://www.mathworks.com/help/simulink/gui/fixedstepsizefundamentalsampletime.html). Thus the stored active verification configuration supplies evidence for a one-second base step. This is a static configuration result, not execution evidence. The saved simulation stops at 100 seconds; no 200-second simulation is established here. A formal model-checking proof could use a different horizon, but none was executed in this follow-up.

`verify_clock_sources.py` independently reads and hashes the pinned Git blobs, matches the named source requirement, follows each SLX active configuration, and checks the exact fields above. It writes a machine-readable receipt. It does not simulate MATLAB/Simulink, compile Lustre, prove the end-to-end export binding, establish continuous-time or deployment behavior, or show a MathGraph advantage.

The original physical-time claim remains UNKNOWN at its frozen input boundary. The narrower stored-configuration fact is now supported by actual author-supplied evidence. The next residual is to qualify the compiled clock and exact model-to-monitor binding, then test evidence addition and withdrawal at that scope. Asking for a new author clarification is no longer the cheapest next step: the repository already supplies the relevant configuration evidence.

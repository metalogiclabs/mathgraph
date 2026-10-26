# Required provider/model feedback — factual engineering record

**Project:** MathGraph Autopilot — evidence-seeking coding agent. **Provider:** Nebius Token Factory. **Model:** `nvidia/nemotron-3-super-120b-a12b` (NVIDIA Nemotron 3 Super).

## What we built

A two-attempt, bounded code-repair loop for an exact pinned public Python repository. Nebius serves the Nemotron coding proposal. Local trusted tooling validates the proposal against a strict single-function AST grammar, executes upstream native tests and newly selected separating tests, then binds the result to source/test hashes. The model's output never constitutes its own completion warrant.

## What worked

- The OpenAI-compatible chat-completions API was straightforward to call from standard-library Python via an environment variable; no dedicated SDK dependency.
- The live run could be executed with a privately configured GitHub Actions secret, without exposing it to the browser demo, public artifacts or ordinary tests.
- The model eventually produced a valid patch for a real, source-pinned native module on the first try after we constrained the output, and the independent tests qualified it. [Successful run #40255882641](https://github.com/metalogiclabs/mathgraph/actions/runs/40255882641).
- Nebius provider request identity (when present) and raw-response digest are useful for tracing and linking the model to separately verifiable engineering results.

## Friction and exact reproducible failure modes

1. **Empty final content:** The initial genuine inference [run #40254932826](https://github.com/metalogiclabs/mathgraph/actions/runs/40254932826) returned no usable message.content. For a bounded short-form code reply, explicit `chat_template_kwargs.enable_thinking=False` prevented the allocated output budget from being spent on reasoning instead of final output. It would help if the docs and examples clearly contrasted reasoning and non-reasoning output/finish modes per Nemotron model.
2. **Malformed JSON:** [Run #40255193578](https://github.com/metalogiclabs/mathgraph/actions/runs/40255193578) produced text that was not syntactically complete JSON. The official guided JSON pattern `guided_json` together with `response_format: {"type":"json_object"}` subsequently made schema output more reliable. A compact model-specific constrained-output cookbook would materially improve initial integration.
3. **Unusable but valid actions:** After JSON conformance, [run #40255411025](https://github.com/metalogiclabs/mathgraph/actions/runs/40255411025) yielded two genuine proposals rejected by the allowed Python syntax/structure. A strict two-statement system instruction plus prior verifier feedback resolved this without weakening the safety gate. Better examples of repair via *typed actions* rather than free-form source text could help high-reliability agent builders.

## Improvements requested

- Model cards and examples should explicitly show the correct `enable_thinking` switches, empty-content diagnostics, finish reasons and suggested `max_tokens` values for brief deterministic outputs.
- Document which `guided_json`, `json_object`, tool-choice and response constraints work with each Nemotron model; demonstrate handling invalid or truncated responses without executing them.
- Offer optional per-request reproducibility metadata such as model revision, request ID, input/output token usage, monetary cost estimate and exact endpoint model identity in normalized response fields. This would make verifiable AI software systems easier to audit.
- Provide a minimal end-to-end **model → typed proposal → independent native tests → source-bound receipt** example to discourage treating model self-report as test authority.

## Onboarding assessment

Once an API key was available, the endpoint was accessible through the GitHub runner. The main integration time was spent reconciling response format, thinking mode and output constraints, rather than on authentication or the HTTP transport.

**Would we build with Nebius Token Factory again?** Yes, for source-constrained, test-verified proposals with explicit provenance. We would first freeze a minimal non-thinking structured-output contract and independent test gate, and retain a precise estimate of cost for repeated agent trials before extending the deployment.

**Scope:** This is factual feedback from a few bounded run attempts, not a measurement of platform uptime, security, latency reliability or large-scale model accuracy. The synthetic UI replay is not evidence of inference; source-linked Actions runs are.

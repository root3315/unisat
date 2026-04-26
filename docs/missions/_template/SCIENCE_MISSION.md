# Science mission — <Mission name>

## 1. Question

State the scientific or engineering question this mission answers in one
sentence. Avoid vague framings like "collect telemetry": commit to a specific
measurable quantity.

## 2. Hypotheses

- **H₀ (null):** what we expect to observe under the no-effect assumption.
- **H₁ (alternative):** what we expect to observe if the effect is real.
- Decision rule: how the collected data will discriminate between H₀ and H₁.

## 3. Sensor selection

For each primary sensor, justify the choice against at least five criteria:

1. Sensitivity to the target signal at the expected magnitude.
2. Mass and power compatibility with the form-factor budget.
3. Interface compatibility with the platform (I²C, SPI, UART, GPIO capture, …).
4. Time response vs. flight phase duration.
5. Heritage / availability under the project's procurement constraints.

## 4. Expected data product

Describe what the mission outputs at the end of the flight:

- Quantity, units, and resolution of the primary measurement.
- Sampling cadence and total sample count.
- File format and where it is stored on the platform.

## 5. Analysis method

Describe the post-flight analysis pipeline. Reference scripts under
`scripts/` and any baseline SITL dataset used for regression testing.

## 6. Originality

State explicitly what makes this mission non-trivial. A jury or reviewer
should be able to read this section and tell why the team is not just
re-running a generic baseline.

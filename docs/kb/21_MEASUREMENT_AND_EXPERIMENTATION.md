# Measurement and Experimentation

## Baseline
Use a fixed/simple recovery policy as the comparison group.

## Primary Metric
**Incremental Revenue Recovered = RecoverAI recovered GMV − baseline recovered GMV**

## Secondary Metrics
- recovery rate
- recovered GMV
- uplift
- intervention success rate
- false-intervention rate/cost
- policy violations
- action failure rate
- expected vs actual recovery
- ROI

## Evaluation Design
Use synthetic controlled data with:
- training/development population
- held-out evaluation population

The hidden outcome generator should encode realistic but controlled relationships rather than pure randomness.

## Example
Illustrative only:
Baseline recovered ₹2.4L from 1,000 failed payments.
RecoverAI recovered ₹3.7L.
Incremental recovery = ₹1.3L.
Uplift = 54%.

These are demo examples only, not measured results.

## Attribution
Attribute recovery to an action only under an explicitly defined attribution window and state transition. Exact attribution window is **TO VALIDATE**.

## ROI
ROI should include recovered contribution value minus action/incentive/operational costs where those costs are modeled.

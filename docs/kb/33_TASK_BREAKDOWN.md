# Task Breakdown

## P0-01
Description: Connect Razorpay Remote MCP and enumerate actual tools.  
Priority: P0. Dependencies: credentials. Expected files: integration notes/config. Acceptance: tool list captured. Testing: connection smoke test.

## P0-02
Description: Verify payment/order read access.  
Priority: P0. Dependencies: P0-01. Acceptance: payment/order context retrieved.

## P0-03
Description: Create Standard Payment Link in Test Mode.  
Priority: P0. Dependencies: P0-01. Acceptance: link created and opened.

## P0-04
Description: Verify success/failure payment outcomes.  
Priority: P0. Dependencies: P0-03. Acceptance: resulting state retrievable.

## P0-05
Description: Validate webhook path.  
Priority: P0. Dependencies: P0-04. Acceptance: event reaches backend.

## P1-01
Description: Create database schema.  
Priority: P0. Dependencies: data model. Acceptance: migrations/seed succeed.

## P1-02
Description: Build controlled synthetic data generator.  
Priority: P0. Dependencies: data model. Acceptance: reproducible train/held-out data.

## P2-01
Description: Implement context builder.  
Priority: P0. Dependencies: P1. Acceptance: structured context produced.

## P2-02
Description: Implement recovery probability model.  
Priority: P0. Dependencies: P1. Acceptance: held-out evaluation available.

## P2-03
Description: Implement decision engine and expected-value scoring.  
Priority: P0. Dependencies: P2-02. Acceptance: candidate ranking works.

## P2-04
Description: Implement guardrail engine.  
Priority: P0. Dependencies: P2-03. Acceptance: disallowed actions blocked.

## P3-01
Description: Implement agent state machine.  
Priority: P0. Dependencies: P2. Acceptance: full loop executes.

## P4-01
Description: Implement Razorpay action adapter.  
Priority: P0. Dependencies: P0. Acceptance: Standard Payment Link action works.

## P4-02
Description: Implement outcome attribution.  
Priority: P0. Dependencies: P0-05. Acceptance: action→outcome linked.

## P5-01
Description: Build recovery queue and decision UI.  
Priority: P1. Dependencies: P3/P4.

## P6-01
Description: Build baseline comparison/evaluation.  
Priority: P0. Dependencies: P1/P2.

## P7-01
Description: Seed demo scenarios and failure injection.  
Priority: P0. Dependencies: P6.

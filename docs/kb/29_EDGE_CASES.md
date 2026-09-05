# Edge Cases

- Payment succeeds before recovery action executes.
- Payment is refunded/terminal.
- Duplicate event arrives.
- Duplicate action request arrives.
- Payment Link creation fails.
- Webhook arrives before local action state is persisted.
- Webhook is delayed.
- Multiple failed attempts exist.
- Customer has repeated failures.
- No eligible strategy exists.
- Model confidence is below threshold.
- High-value transaction requires approval.
- Synthetic data has missing fields.
- External MCP tool is unavailable.
- Action succeeds but outcome is not immediately observable.

Every edge case must have a deterministic safe behavior.

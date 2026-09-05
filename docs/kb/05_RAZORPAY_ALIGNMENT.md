# Razorpay Alignment

## Verified Research Direction
Razorpay's ecosystem includes payment infrastructure, recovery capabilities, Agent Studio, and an MCP layer exposing payment-related tools.

Relevant documented capabilities from the project research include:
- Payment fetching and payment status/failure fields.
- Order and order-payment retrieval.
- Standard Payment Links.
- Agent Studio specialist agents including Subscription Recovery and Abandoned Cart Conversion.
- Razorpay MCP with payment, order, payment-link and other tools.

## Complement
RecoverAI is positioned as an adaptive decision/orchestration layer. It can use Razorpay data and supported actions while adding contextual selection and outcome measurement.

## Does Not Replace
- Payment Gateway infrastructure.
- Existing Razorpay recovery systems.
- Specialist Agent Studio capabilities.
- Razorpay's internal routing/retry infrastructure.

## Identified Gap
The research identified a decision gap between detecting a failed payment and choosing the optimal intervention for that individual context.

## Integration Opportunity
MVP read capabilities:
- fetch payment
- fetch payments
- fetch order
- fetch all orders
- fetch order payments
- payment-link reads where needed

MVP action capabilities:
- create Standard Payment Link
- send Standard Payment Link
- update/read Payment Link where required

## Important Test-Mode Constraint
UPI Payment Links are not supported in Razorpay Test Mode. Therefore the demo must not depend on UPI Payment Links.

## Verification Rule
Exact tool availability must be verified in the team's actual MCP connection before implementation. Do not assume a tool exists merely because it appears in historical research.

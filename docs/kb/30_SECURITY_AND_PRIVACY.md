# Security and Privacy

## Requirements
- Keep Razorpay/API secrets on the backend.
- Never commit secrets.
- Do not expose credentials to the frontend.
- Validate webhook authenticity according to the chosen integration's official requirements.
- Use least-privilege access where supported.
- Log actions without unnecessarily storing sensitive payment data.
- Separate synthetic/demo data from real customer data.

## Privacy
Exact personal-data retention, consent, communications, and regulatory requirements are **TO VALIDATE** for the deployment context.

## Audit
Store decision/action metadata needed to reconstruct what happened without storing unnecessary sensitive information.

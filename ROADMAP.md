# Implementation roadmap

## Implemented now

- Fixture-backed material exposure, recovery options, evidence, simulation, and qualification.
- Versioned case state with approval validation, idempotent mock action receipt, and audit trace.
- Local web application and Cloud Foundry deployment.
- SAP AI Core adapter for the explicit Review AI action.
- Joule read-only capability for current material exposure.

## Next implementation slice

1. Add Joule functions for recovery options, AI review result, and approval status.
2. Test exposure -> Review AI -> human approval -> mock receipt end to end.
3. Replace one fixture-backed read adapter with a read-only SAP endpoint.
4. Keep fixture mode as an explicit fallback for local/demo operation.

## Future implementation

AWS EventBridge/Lambda can trigger the workflow, S3 can store evidence and audit
versions, and Amazon Bedrock can be evaluated as an alternative model provider.
These services are not required for the current demo and should be introduced
only after the read-only SAP integration is stable.

# Azure Connector Design Proposal - AEV Pod Delta

**Status:** Week 2 Integration Squad Design Proposal\
**Owner:** Vatsal Thummar\
**Scope:** Azure Connector\
**Purpose:** Define the Integration-side design for the Azure connector
before implementation.

> This document is a design proposal. It does not finalize SDK
> implementation details or platform ingestion details that are not yet
> specified.

------------------------------------------------------------------------

## 1. Scope

The Azure connector is responsible for connecting the AEV Integration
Hub with Azure and supporting discovery and ingestion of Azure
resources.

The documented Azure connector scope includes:

-   Service principal authentication
-   Reader role
-   Multi-subscription support
-   Multi-tenant support
-   Virtual Machines
-   Storage
-   Azure Active Directory (AAD)
-   SQL
-   Functions
-   Data normalization
-   Push of discovered assets to the platform
-   Unit testing
-   Integration testing
-   Documentation

------------------------------------------------------------------------

## 2. Connector Contract

The Azure connector is designed against the Week 1 Connector Interface
Contract proposal. Final implementation must follow the contract agreed
with the Connector SDK squad.

The documented methods are:

``` python
async discover(config: dict) -> AsyncIterator[Asset]
async ingest(config: dict) -> AsyncIterator[dict]
async sync(config: dict, direction: str) -> SyncResult
async health_check(config: dict) -> dict
config_schema() -> dict
credential_schema() -> dict
```

The documented `Asset` model contains:

-   `external_id`
-   `name`
-   `type`
-   `attributes`
-   `tags`

The documented `SyncResult` model contains:

-   `records_processed`
-   `records_created`
-   `records_updated`
-   `records_failed`
-   `error`

The final SDK implementation of these interfaces is dependent on the
Connector SDK work.

------------------------------------------------------------------------

## 3. Azure Authentication

The documented authentication approach is:

-   Azure Service Principal
-   Reader role

The connector must use the approved project authentication and
credential mechanism once the SDK and configuration contract are
finalized.

### Not Yet Specified

The source documents do not specify:

-   Exact credential field names
-   Exact environment variable names
-   Credential storage mechanism
-   Credential passing format
-   Token caching behavior

These remain:

**TBD - requires agreement with the Connector SDK/platform team.**

------------------------------------------------------------------------

## 4. Azure Resource Discovery

The connector must support discovery of the following Azure resource
categories:

  Resource                       Required
  ------------------------------ ----------
  Virtual Machines               Yes
  Storage                        Yes
  Azure Active Directory (AAD)   Yes
  SQL                            Yes
  Functions                      Yes

Discovery should produce resources in the standardized `Asset`
representation defined by the Connector Interface Contract proposal.

------------------------------------------------------------------------

## 5. Asset Normalization

The documented `Asset` model contains:

-   `external_id`
-   `name`
-   `type`
-   `attributes`
-   `tags`

Each discovered Azure resource must be normalized into this common
representation.

### Resource Mapping

The exact Azure-to-Asset field mapping is not yet finalized.

For each resource type, the Azure connector implementation will need to
determine an appropriate mapping to the standardized Asset fields. The
exact mapping is not specified by the source documents and therefore
remains subject to agreement.

The intended mapping areas are:

-   Azure resource identifier → `external_id`
-   Resource name → `name`
-   Resource category → `type`
-   Additional resource information → `attributes`
-   Applicable classification information → `tags`

### Important

The exact keys and values inside `attributes` and `tags` are not
specified by the source documents.

Therefore:

**TBD - requires agreement before finalizing the normalization schema.**

------------------------------------------------------------------------

## 6. Multi-Subscription Support

The Azure connector must support multiple Azure subscriptions.

The exact configuration mechanism for selecting or discovering
subscriptions is not specified.

### TBD

-   Subscription selection configuration
-   Subscription discovery behavior
-   Whether all accessible subscriptions are scanned by default
-   Per-subscription filtering

These decisions require agreement with the SDK/platform design.

------------------------------------------------------------------------

## 7. Multi-Tenant Support

The Azure connector must support multi-tenant environments.

The exact tenant configuration and credential relationship are not
specified.

### TBD

-   Tenant configuration format
-   Whether one connector instance can operate across multiple tenants
-   Tenant/subscription relationship
-   Credential handling across tenants

These decisions require agreement with the SDK/platform design.

------------------------------------------------------------------------

## 8. Connector Operations

### 8.1 `discover()`

Responsible for discovering supported Azure resources and returning them
as standardized `Asset` objects.

### 8.2 `ingest()`

Responsible for providing discovered/source data in the connector
contract's ingestion representation.

### 8.3 `sync()`

Responsible for synchronization according to the direction specified by
the connector contract.

The valid values for `direction` are not yet specified.

### 8.4 `health_check()`

Responsible for checking Azure connectivity.

The exact health response structure is not yet specified.

### 8.5 `config_schema()`

Responsible for describing the connector configuration requirements.

The exact schema format is not yet specified.

### 8.6 `credential_schema()`

Responsible for describing the connector credential requirements.

The exact schema format is not yet specified.

------------------------------------------------------------------------

## 9. Platform Integration

The documented requirement is that discovered assets are pushed to the
AEV platform.

However, the current project documentation does not specify the final
platform ingestion API, service, message queue, or other transport
mechanism.

Therefore:

**TBD - platform ingestion mechanism requires clarification.**

The Azure connector should not invent an ingestion mechanism.

------------------------------------------------------------------------

## 10. Testing Strategy

Testing should cover the documented Azure connector responsibilities.

### 10.1 Unit Testing

Tests should eventually cover:

-   Azure authentication behavior
-   Resource discovery
-   Resource normalization
-   Connector operations
-   Error handling

The exact testing framework and coverage configuration should follow the
project's established backend testing conventions.

### 10.2 Integration Testing

Integration testing should verify Azure connector behavior against Azure
or an approved mock/test environment.

The exact Azure test environment and credentials are not specified.

------------------------------------------------------------------------

## 11. Implementation Dependencies

The current repository does not yet contain the following
connector-related implementation components:

-   Connector SDK abstract base class
-   Asset model
-   SyncResult model
-   Configuration/credential schema convention
-   Platform ingestion interface

These components affect the final end-to-end Azure implementation.

The Azure-specific design and planning can proceed in parallel while
these dependencies are resolved.

------------------------------------------------------------------------

## 12. Open Decisions

The following require resolution before the Azure connector is
considered finalized:

1.  Credential passing mechanism
2.  Configuration schema format
3.  Credential schema format
4.  Azure-to-Asset attribute mapping
5.  Azure-to-Asset tag mapping
6.  Multi-subscription configuration
7.  Multi-tenant configuration
8.  Sync direction values
9.  Platform ingestion mechanism
10. Error handling conventions

------------------------------------------------------------------------

## 13. Current Status

### Completed

-   Azure connector scope identified
-   Authentication approach documented
-   Required Azure resource categories identified
-   Asset normalization approach documented
-   Multi-subscription requirement documented
-   Multi-tenant requirement documented
-   SDK/platform dependencies identified

### Pending

-   Connector SDK implementation
-   Shared Asset and SyncResult models
-   Configuration and credential schema decisions
-   Final Azure asset mappings
-   Platform ingestion mechanism
-   Azure implementation and tests

------------------------------------------------------------------------

## 14. References

-   AEV Platform - Pod Delta Build Guide
-   Week 1 Connector Interface Contract
-   Phase 1 Integration execution plan

# Week 1 Connector Interface Contract - AEV Pod Delta

**Status:** Week 1 Integration Squad Proposal (Not Yet Finalized)  
**Purpose:** Document the standardized interface contract that all data connectors must implement  
**Scope:** Python Connector SDK interface specification  
**Date:** 2026-08-11  
**Note:** This document is a review artifact for internal Integration squad progress. Final approval requires joint agreement with the Connector SDK squad.

---

## 1. Contract Purpose

The Connector Interface defines a standardized contract that all data source connectors must implement to integrate with the AEV Platform Pod Delta. This contract specifies:

- **Six required methods** that connectors must provide
- **Two required data models** (Asset and SyncResult) that connectors must use
- **Method signatures** including parameters and return types
- **Async/await patterns** for I/O-bound operations
- **Streaming support** for large-scale data discovery and ingestion

The contract enables the Integration squad to:
- Discover available data assets from any source
- Ingest data streams from connectors
- Synchronize data according to the direction specified by the connector contract.
- Verify connector health
- Query connector requirements dynamically
- Support enterprise integrations without reimplementation for each data source

---

## 2. Connector Methods - Exact Signatures

All connector implementations must provide the following six methods:

```python
async def discover(self, config: dict) -> AsyncIterator[Asset]

async def ingest(self, config: dict) -> AsyncIterator[dict]

async def sync(self, config: dict, direction: str) -> SyncResult

async def health_check(self, config: dict) -> dict

def config_schema(self) -> dict

def credential_schema(self) -> dict
```

---

## 3. Method Specifications

### 3.1 `async discover(self, config: dict) -> AsyncIterator[Asset]`

**Capability:** Discover Data  
**Method Type:** Asynchronous  
**Execution Model:** Returns streaming async iterator

**Purpose:**  
Enumerate all available data assets in the source system. The method returns an asynchronous iterator that yields Asset objects one at a time, enabling efficient streaming discovery of large asset catalogs without loading all results into memory.

**Parameters:**
- `config: dict` - Configuration parameters required by the connector (TBD: structure and keys)

**Return Type:**
- `AsyncIterator[Asset]` - Asynchronous iterator that yields Asset objects

**Specified by Source:**
- ✅ Method name: `discover`
- ✅ Async/await pattern: yes
- ✅ Parameter type: `dict`
- ✅ Return type: `AsyncIterator[Asset]`

**Not Yet Specified (TBD):**
- ❌ Structure and required keys in `config` dict
- ❌ Whether `config` can be empty
- ❌ Error handling: which exceptions are raised on failure
- ❌ Timeout behavior or maximum execution time
- ❌ Whether discovery includes or excludes archived/inactive assets
- ❌ Ordering guarantees for discovered assets
- ❌ Deduplication behavior if assets appear multiple times
- ❌ Pagination or cursor support for resuming partial discovery
- ❌ Rate limiting or backpressure mechanism
- ❌ Maximum number of assets discoverable per connector

---

### 3.2 `async ingest(self, config: dict) -> AsyncIterator[dict]`

**Capability:** Ingest Data  
**Method Type:** Asynchronous  
**Execution Model:** Returns streaming async iterator

**Purpose:**  
Stream raw data records from the source system. The method returns an asynchronous iterator that yields dictionary objects representing individual data records, enabling continuous ingestion of large datasets without buffering in memory.

**Parameters:**
- `config: dict` - Configuration parameters required by the connector (TBD: structure and keys)

**Return Type:**
- `AsyncIterator[dict]` - Asynchronous iterator that yields dictionary objects (record format TBD)

**Specified by Source:**
- ✅ Method name: `ingest`
- ✅ Async/await pattern: yes
- ✅ Parameter type: `dict`
- ✅ Return type: `AsyncIterator[dict]`

**Not Yet Specified (TBD):**
- ❌ Structure and required keys in `config` dict
- ❌ Whether `config` can be empty
- ❌ Structure of returned dict objects (required keys, schema)
- ❌ Whether returned dicts have a unique identifier field
- ❌ Relationship to `discover()`: are ingested records mapped to discovered assets?
- ❌ Whether `ingest()` retrieves all data or can filter by asset/criteria
- ❌ Error handling: which exceptions are raised on failure
- ❌ Whether ingest is a one-time full pull or incremental/continuous stream
- ❌ Time window or date range filtering options
- ❌ Timeout behavior or maximum execution time
- ❌ Deduplication of records across multiple ingest calls
- ❌ Data transformation responsibility (raw vs normalized)

---

### 3.3 `async sync(self, config: dict, direction: str) -> SyncResult`

**Capability:** Sync  
**Method Type:** Asynchronous  
**Execution Model:** Single operation that returns result summary

**Purpose:**  
Synchronize data between the source system and destination. The sync operation is unidirectional per call, controlled by the `direction` parameter. Returns a SyncResult summary of records processed, created, updated, failed, and any errors encountered.

**Parameters:**
- `config: dict` - Configuration parameters required by the connector (TBD: structure and keys)
- `direction: str` - Direction of sync operation (TBD: valid string values and semantics)

**Return Type:**
- `SyncResult` - Summary of sync operation results

**Specified by Source:**
- ✅ Method name: `sync`
- ✅ Async/await pattern: yes
- ✅ Parameters: `config: dict`, `direction: str`
- ✅ Return type: `SyncResult`

**Not Yet Specified (TBD):**
- ❌ Valid string values for `direction` parameter (e.g., "push", "pull", "to_source", "to_target", etc.)
- ❌ Semantics of `direction` values and what operations they control
- ❌ Whether sync is incremental or full dataset
- ❌ Structure and required keys in `config` dict
- ❌ Whether `config` can be empty
- ❌ Transaction semantics: all-or-nothing vs partial success
- ❌ Idempotency guarantee: same config and direction yields same result
- ❌ Conflict resolution strategy (if applicable)
- ❌ Error handling: which exceptions are raised on failure
- ❌ Retry and recovery behavior on transient failures
- ❌ Timeout behavior or maximum execution time
- ❌ How SyncResult counts (processed, created, updated, failed) are computed
- ❌ Atomicity of SyncResult field updates

---

### 3.4 `async health_check(self, config: dict) -> dict`

**Capability:** Check Health  
**Method Type:** Asynchronous  
**Execution Model:** Single operation that returns status dictionary

**Purpose:**  
Verify that the source system is accessible and operational. Returns a dictionary containing health status information, enabling the Integration squad to verify connector readiness before executing discover, ingest, or sync operations.

**Parameters:**
- `config: dict` - Configuration parameters required by the connector (TBD: structure and keys)

**Return Type:**
- `dict` - Health status dictionary (structure and keys TBD)

**Specified by Source:**
- ✅ Method name: `health_check`
- ✅ Async/await pattern: yes
- ✅ Parameter type: `dict`
- ✅ Return type: `dict`

**Not Yet Specified (TBD):**
- ❌ Structure and required keys in returned `dict`
- ❌ How to interpret health status (e.g., "status": "healthy", boolean flag, etc.)
- ❌ Required dictionary keys indicating pass/fail
- ❌ Metrics included in response (latency, uptime, version, etc.)
- ❌ Whether health_check should attempt data operations or only connectivity
- ❌ Error handling: whether health_check raises exceptions or returns error status in dict
- ❌ Timeout behavior or maximum execution time
- ❌ Caching of health status results
- ❌ Structure and required keys in `config` dict
- ❌ Whether `config` can be empty

---

### 3.5 `def config_schema(self) -> dict`

**Capability:** Describe Connector Configuration  
**Method Type:** Synchronous (non-async)  
**Execution Model:** Single query, no I/O

**Purpose:**  
Return a schema describing all configuration parameters that the connector requires. This enables the Integration squad to dynamically generate UI forms, validate user-provided configuration, and document connector requirements without hardcoding connector-specific logic.

**Parameters:**
- None (self only)

**Return Type:**
- `dict` - Configuration schema (format and structure TBD)

**Specified by Source:**
- ✅ Method name: `config_schema`
- ✅ Synchronous (non-async)
- ✅ No parameters beyond self
- ✅ Return type: `dict`

**Not Yet Specified (TBD):**
- ❌ Schema format (JSON Schema, Pydantic format, custom dict, other)
- ❌ Schema version or versioning strategy
- ❌ How to validate a config dict against the returned schema
- ❌ Required vs optional configuration keys
- ❌ Field types, descriptions, and documentation
- ❌ Default values for configuration parameters
- ❌ Example configurations
- ❌ Whether schema is static or can change based on connector state
- ❌ Constraints on field values (min/max, patterns, enums)
- ❌ Dependency relationships between config fields
- ❌ Relationship between config_schema() and credential_schema() outputs

---

### 3.6 `def credential_schema(self) -> dict`

**Capability:** Describe Connector Credentials  
**Method Type:** Synchronous (non-async)  
**Execution Model:** Single query, no I/O

**Purpose:**  
Return a schema describing all credential parameters that the connector requires. This enables the Integration squad to dynamically generate secure credential input forms, validate user-provided credentials, and document credential requirements without hardcoding connector-specific logic.

**Parameters:**
- None (self only)

**Return Type:**
- `dict` - Credential schema (format and structure TBD)

**Specified by Source:**
- ✅ Method name: `credential_schema`
- ✅ Synchronous (non-async)
- ✅ No parameters beyond self
- ✅ Return type: `dict`

**Not Yet Specified (TBD):**
- ❌ Schema format (JSON Schema, Pydantic format, custom dict, other)
- ❌ Schema version or versioning strategy
- ❌ How to validate credentials against the returned schema
- ❌ Credential field types (API key, username/password, token, certificate, etc.)
- ❌ Required vs optional credential fields
- ❌ Field descriptions, documentation, and security considerations
- ❌ Whether certain fields should be masked/redacted in logs
- ❌ Example credential formats
- ❌ Credential storage responsibility (Integration squad vs Connector)
- ❌ Credential encryption or protection requirements
- ❌ How credentials are passed to other methods (merged into config, separate parameter, etc.)
- ❌ Credential expiration and rotation handling
- ❌ Constraints on credential field values (patterns, length, allowed characters)
- ❌ Dependency relationships between credential fields
- ❌ Relationship between config_schema() and credential_schema() outputs

---

## 4. Data Models

### 4.1 Asset

**Purpose:**  
Represents a single data asset (table, dataset, object, entity) discoverable in the source system. Returned by the `discover()` method.

**Fields:**

```python
class Asset:
    external_id: str      # Unique identifier in source system
    name: str             # Human-readable asset name
    type: str             # Asset category/type
    attributes: dict      # Additional asset properties
    tags: dict            # Metadata tags/labels
```

**Field Specifications:**

| Field | Type | Source | Purpose |
|-------|------|--------|---------|
| `external_id` | `str` | ✅ Specified | Unique identifier for this asset within the source system |
| `name` | `str` | ✅ Specified | Human-readable name of the asset |
| `type` | `str` | ✅ Specified | Category or type of asset |
| `attributes` | `dict` | ✅ Specified | Additional asset properties (keys and values TBD) |
| `tags` | `dict` | ✅ Specified | Metadata labels/tags (keys and values TBD) |

**Not Yet Specified (TBD):**
- ❌ Validation rules for `external_id` (non-empty, max length, format constraints)
- ❌ Validation rules for `name` (non-empty, max length, allowed characters)
- ❌ Allowed values for `type` field (enumerated list or free text?)
- ❌ Allowed keys in `attributes` dict
- ❌ Allowed values for `attributes` dict values (types, ranges, formats)
- ❌ Allowed keys in `tags` dict
- ❌ Allowed values for `tags` dict values
- ❌ Whether any fields are optional or all required
- ❌ Default values for any fields
- ❌ Maximum size of `attributes` and `tags` dicts
- ❌ Serialization format (JSON, Protocol Buffers, etc.)
- ❌ Whether Asset should have additional metadata fields (created_at, modified_at, owner, etc.)

---

### 4.2 SyncResult

**Purpose:**  
Summary result of a sync operation. Returned by the `sync()` method. Contains counters and error information.

**Fields:**

```python
class SyncResult:
    records_processed: int     # Number of records processed
    records_created: int       # Number of records created
    records_updated: int       # Number of records updated
    records_failed: int        # Number of records that failed
    error: str | None          # Error message if sync failed, None otherwise
```

**Field Specifications:**

| Field | Type | Source | Purpose |
|-------|------|--------|---------|
| `records_processed` | `int` | ✅ Specified | Count of records processed during sync |
| `records_created` | `int` | ✅ Specified | Count of records created during sync |
| `records_updated` | `int` | ✅ Specified | Count of records updated during sync |
| `records_failed` | `int` | ✅ Specified | Count of records that failed during sync |
| `error` | `str \| None` | ✅ Specified | Error message if sync encountered fatal error, None if success |

**Not Yet Specified (TBD):**
- ❌ Whether counts are cumulative (total) or per-sync-operation
- ❌ Semantics of "processed": records pulled, validated, attempted, other?
- ❌ Semantics of "created" vs "updated": rules for distinguishing them
- ❌ Whether sync can partially fail (error set while some counts > 0)
- ❌ Whether partial failure should be retried or considered final
- ❌ Error message format or error code schema
- ❌ Whether SyncResult should include warnings in addition to errors
- ❌ Validation rules: e.g., records_created + records_updated must equal records_processed?
- ❌ Handling of negative counts (should ever occur?)
- ❌ Whether records_processed should equal records_created + records_updated + records_failed
- ❌ Additional metadata (start time, end time, duration, sync ID, etc.)
- ❌ Whether error field should include structured error details (code, type, cause)

---

## 5. Specified vs Not Yet Specified Summary

### Fully Specified by Source ✅
- All six method names
- All method signatures (parameters and return types)
- Async/await usage for discover, ingest, sync, health_check
- Synchronous (non-async) for config_schema, credential_schema
- All Asset field names and types
- All SyncResult field names and types
- Iterator-based return for discover and ingest
- Dictionary return for health_check, config_schema, credential_schema

### Not Yet Specified (TBD) ❌

**Configuration and Credentials:**
- ❌ Structure of `config` dict parameter (required/optional keys)
- ❌ Relationship between `config_schema()`, `credential_schema()`, and `config` dict parameter
- ❌ Whether credentials are part of `config` or passed separately
- ❌ Credential storage and passing mechanism

**Sync Direction:**
- ❌ Valid string values for `direction` parameter
- ❌ Semantics of each direction value

**Error Handling:**
- ❌ Which methods raise exceptions vs return error state
- ❌ Exception types and messages
- ❌ Error recovery and retry logic

**Data Structures:**
- ❌ Structure of dicts returned by `ingest()`, `health_check()`, `config_schema()`, `credential_schema()`
- ❌ Allowed keys and value types in returned dicts
- ❌ Validation schemas and rules

**Operation Semantics:**
- ❌ Full vs incremental for discover, ingest, sync
- ❌ Idempotency guarantees
- ❌ Transaction boundaries and atomicity
- ❌ Timeout and rate limiting behavior
- ❌ Streaming backpressure mechanism
- ❌ Deduplication rules

**Data Model Validation:**
- ❌ Required vs optional Asset fields
- ❌ Asset field constraints and validation
- ❌ SyncResult field semantics and relationships
- ❌ Data type constraints and ranges

---

## 6. Unresolved Contract Decisions

The following critical decisions require joint agreement between the Integration squad and the Connector SDK squad before finalizing this contract:

### 6.1 Configuration and Credential Passing Mechanism
**Issue:** The contract specifies `config: dict` parameter for four methods, but does not define:
- What keys and structure this dict should have
- Whether credentials are merged into `config` or passed separately
- How `config_schema()` and `credential_schema()` relate to the actual `config` dict passed to methods

**Resolution Required:** Joint workshop to agree on:
- Single merged config+credential dict vs separate parameters
- Config dict structure and required keys
- How schema methods describe the actual parameter structure
- Integration squad form generation and validation logic

---

### 6.2 Sync Direction Parameter Values
**Issue:** `sync()` method requires `direction: str` parameter, but does not define valid values:
- Possible values might be: "push", "pull", "upstream", "downstream", "to_source", "to_target", "bidirectional"
- Connector implementations need to know which values to support
- Integration squad needs to know which strings to pass

**Resolution Required:** Joint workshop to agree on:
- Standard direction value names and semantics
- Whether bidirectional sync is supported or separate calls required
- Conflict resolution for bidirectional operations
- Error handling for unsupported direction values

---

### 6.3 Error Handling and Exception Strategy
**Issue:** Contract does not specify how errors are reported:
- `discover()` and `ingest()` are iterators—how do they signal errors?
- `sync()` has `error` field—should it also raise exceptions?
- `health_check()` has dict return—how does it indicate failure?
- What exception types should connectors raise?

**Resolution Required:** Joint workshop to agree on:
- Which methods raise exceptions vs return error state
- Standard exception types for different error categories
- Error message format and content
- Partial failure handling (e.g., some records ingested before error)
- Whether errors should be user-facing or internal

---

### 6.4 Data Structure Specifications
**Issue:** Contract specifies return types but not structure details:
- `ingest()` returns `AsyncIterator[dict]` but dict structure is unspecified
- `health_check()` returns `dict` but required keys are unspecified
- `config_schema()` and `credential_schema()` return `dict` but format is unspecified

**Resolution Required:** Joint workshop to agree on:
- Schema format standard (JSON Schema, Pydantic, custom dict format)
- Required keys and value types for each returned dict
- Validation rules and constraints
- Examples and documentation format
- How Integration squad consumes and validates these structures

---

### 6.5 Asset and SyncResult Field Semantics
**Issue:** Data models specify field names and types but not semantics:
- `Asset.attributes` and `Asset.tags` are `dict`—what keys/values are allowed?
- `Asset.type`—is it an enum or free text?
- `SyncResult` counts—what exactly do they measure?
- Can sync partially fail (error set with non-zero counts)?

**Resolution Required:** Joint workshop to agree on:
- Allowed keys in Asset.attributes and Asset.tags
- Whether Asset.type is enumerated or free-form
- Definition of "processed", "created", "updated", "failed" for SyncResult
- Validation rules: which fields are required, which optional
- Constraints: field size limits, value ranges, format patterns

---

### 6.6 Async Iterator Semantics
**Issue:** `discover()` and `ingest()` return async iterators, but behavior is unspecified:
- Can iterators be consumed multiple times?
- What happens on connection loss mid-iteration?
- Are partial results returned before error?
- Is ordering guaranteed?
- Is there backpressure/flow control?

**Resolution Required:** Joint workshop to agree on:
- Iterator consumption model (single-use or reusable)
- Error handling within iteration (continue vs fail fast)
- Partial result guarantees
- Ordering and deduplication
- Buffering and flow control strategy

---

## 7. Integration Squad Responsibilities (Week 1 and Beyond)

The Integration squad owns the following based on this contract:

- **Consume connector methods:** Call discover(), ingest(), sync(), health_check()
- **Form generation:** Use config_schema() and credential_schema() to generate UX forms
- **Config validation:** Validate user-provided configuration against schemas
- **Credential management:** Securely store, encrypt, and inject credentials
- **Error handling:** Handle exceptions and error states from connectors
- **Stream processing:** Consume async iterators and buffer/process results
- **Result interpretation:** Parse health_check() and SyncResult responses
- **User feedback:** Display discovery/ingest/sync progress and errors to users

---

## 8. Connector SDK Squad Responsibilities (To Be Coordinated)

The Connector SDK squad owns the following based on this contract:

- **Implement Connector ABC:** Provide base class for all connectors
- **Implement methods:** Provide concrete implementations of the six methods
- **Handle config:** Parse and validate configuration according to config_schema()
- **Handle credentials:** Parse and validate credentials according to credential_schema()
- **Connect to source:** Manage connections to source systems
- **Data transformation:** Convert source data to Asset, dict, and SyncResult formats
- **Error handling:** Raise appropriate exceptions or set error fields
- **Stream generation:** Yield Asset and dict objects in async iterators
- **Sync logic:** Implement directional sync with appropriate semantics

---

## 9. Document Status and Next Steps

**Current Status:** Week 1 Integration Squad Proposal

This document represents the Integration squad's understanding of the documented Connector contract from the AEV Pod Delta Build Guide. It is **not yet approved** and **not yet the final SDK specification**.

**Approval Status:**
- ❌ **Not approved by Connector SDK squad** - Awaiting their review and agreement
- ✅ **Extracted directly from source documentation** - All method signatures and data models are from documented spec
- ⚠️ **Gaps identified** - Unresolved decisions are clearly marked

**Next Steps (Require Connector SDK Coordination):**

1. **Joint Review Workshop**
   - Integration squad presents this contract
   - Connector SDK squad reviews and identifies gaps from their perspective
   - Both squads discuss and resolve the 6 unresolved decision areas

2. **Contract Finalization**
   - Agree on configuration structure and credential passing
   - Agree on sync direction values and semantics
   - Agree on error handling strategy
   - Agree on data structure specifications
   - Agree on field semantics and validation
   - Agree on async iterator behavior

3. **Week 2 Deliverable**
   - Finalized contract document with all decisions resolved
   - Connector ABC implementation (Connector SDK)
   - Asset and SyncResult models (Shared)
   - Configuration and credential schema implementations
   - Integration client code to consume connectors
   - Connector tests and examples

---

## 10. References

**Source Document:** AEV Pod Delta Build Guide - Python Connector Contract Specification

**Methods Documented:**
- async discover(self, config: dict) -> AsyncIterator[Asset]
- async ingest(self, config: dict) -> AsyncIterator[dict]
- async sync(self, config: dict, direction: str) -> SyncResult
- async health_check(self, config: dict) -> dict
- config_schema(self) -> dict
- credential_schema(self) -> dict

**Data Models Documented:**
- Asset: external_id (str), name (str), type (str), attributes (dict), tags (dict)
- SyncResult: records_processed (int), records_created (int), records_updated (int), records_failed (int), error (str | None)

---

**Document Created:** 2026-08-11  
**Prepared By:** Integration Squad - Week 1 Connector Interface Definition Task  
**Classification:** Internal Review Artifact (Not Final)

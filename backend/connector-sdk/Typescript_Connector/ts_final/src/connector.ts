/**
 * The shared Connector contract.
 *
 * Every connector (AWS, Azure, GCP, CrowdStrike, Splunk, Jira, Okta, ...)
 * must extend Connector and implement these 6 methods. This is the
 * TS mirror of the Python ABC frozen jointly with the Integration squad
 * in Week 1 -- once frozen, no connector should need to change its shape.
 */

import { Asset, SyncResult, SyncStatus } from "./models.js";

/** Shape returned by describeConfig()/describeCredentials(): a JSON-Schema-like object. */
export type JsonSchemaLike = Record<string, unknown>;

/**
 * Render a thrown value the way Python's f"{exc}" does -- the message
 * only, without the "Error: " class prefix that JS template literals add.
 */
function formatError(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

export abstract class Connector {
  /**
   * Short unique name for this connector, e.g. "aws", "okta".
   * Defaults to "unnamed", matching the Python class attribute.
   */
  readonly name: string = "unnamed";

  // ---- 1. Discover ------------------------------------------------------

  /**
   * Find and return all assets currently visible to this connector.
   * Should not have side effects on the platform -- just reads from
   * the source system and returns normalized Asset objects.
   */
  abstract discover(): Promise<Asset[]>;

  // ---- 2. Ingest --------------------------------------------------------

  /**
   * Push a batch of discovered assets into the platform's asset service.
   * Returns the number of assets successfully pushed.
   */
  abstract ingest(assets: Asset[]): Promise<number>;

  // ---- 3. Sync ----------------------------------------------------------

  /**
   * Run a full discover -> ingest cycle and report the outcome.
   * Has a default implementation built on discover()/ingest(), but
   * connectors may override it for custom batching, retries, or
   * incremental sync logic.
   */
  async sync(): Promise<SyncResult> {
    const startedAt = new Date();
    const errors: string[] = [];
    let assets: Asset[] = [];

    try {
      assets = await this.discover();
    } catch (exc) {
      errors.push(`discover() failed: ${formatError(exc)}`);
    }

    let pushed = 0;
    if (assets.length > 0) {
      try {
        pushed = await this.ingest(assets);
      } catch (exc) {
        errors.push(`ingest() failed: ${formatError(exc)}`);
      }
    }

    let status: SyncStatus;
    if (errors.length > 0 && pushed === 0) {
      status = SyncStatus.FAILED;
    } else if (errors.length > 0) {
      status = SyncStatus.PARTIAL;
    } else {
      status = SyncStatus.SUCCESS;
    }

    return SyncResult.parse({
      connector: this.name,
      status,
      assets_discovered: assets.length,
      assets_pushed: pushed,
      errors,
      started_at: startedAt,
      finished_at: new Date(),
    });
  }

  // ---- 4. Health check --------------------------------------------------

  /**
   * Return true if the connector can currently reach its source system
   * (credentials valid, network reachable, etc).
   */
  abstract checkHealth(): Promise<boolean>;

  // ---- 5. Describe config -----------------------------------------------

  /**
   * Return a JSON-schema-like object describing what configuration
   * fields this connector needs (excluding credentials).
   */
  abstract describeConfig(): JsonSchemaLike;

  // ---- 6. Describe credentials ------------------------------------------

  /**
   * Return a JSON-schema-like object describing what credential
   * fields this connector needs (e.g. api_key, access_key/secret_key).
   */
  abstract describeCredentials(): JsonSchemaLike;
}
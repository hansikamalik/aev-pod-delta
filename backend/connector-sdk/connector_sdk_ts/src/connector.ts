/**
 * The shared Connector contract.
 *
 * Every connector (AWS, Azure, GCP, CrowdStrike, Splunk, Jira, Okta, ...)
 * must extend Connector and implement these 6 methods. This is the
 * TS mirror of the Python ABC frozen jointly with the Integration squad
 * in Week 1 -- once frozen, no connector should need to change its shape.
 */
import { Asset, SyncResult, SyncStatus } from "./models.js";

export abstract class Connector {
  /** Short unique name for this connector, e.g. "aws", "okta". */
  abstract readonly name: string;

  // ---- 1. Discover ------------------------------------------------------
  /**
   * Find and return all assets currently visible to this connector.
   * Should not have side effects on the platform -- just reads from
   * the source system and returns normalized Asset objects.
   */
  abstract discover(): Promise<Asset[]>;

  // ---- 2. Ingest ----------------------------------------------------------
  /**
   * Push a batch of discovered assets into the platform's asset service.
   * Returns the number of assets successfully pushed.
   */
  abstract ingest(assets: Asset[]): Promise<number>;

  // ---- 3. Sync --------------------------------------------------------
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
      errors.push(`discover() failed: ${exc}`);
    }

    let pushed = 0;
    if (assets.length > 0) {
      try {
        pushed = await this.ingest(assets);
      } catch (exc) {
        errors.push(`ingest() failed: ${exc}`);
      }
    }

    let status: SyncStatus;
    if (errors.length > 0 && pushed === 0) {
      status = "failed";
    } else if (errors.length > 0) {
      status = "partial";
    } else {
      status = "success";
    }

    return SyncResult.parse({
      connector: this.name,
      status,
      assetsDiscovered: assets.length,
      assetsPushed: pushed,
      errors,
      startedAt,
      finishedAt: new Date(),
    });
  }

  // ---- 4. Health check --------------------------------------------------
  /**
   * Return true if the connector can currently reach its source system
   * (credentials valid, network reachable, etc).
   */
  abstract checkHealth(): Promise<boolean>;

  // ---- 5. Describe config -------------------------------------------------
  /**
   * Return a JSON-schema-like object describing what configuration
   * fields this connector needs (excluding credentials).
   */
  abstract describeConfig(): Record<string, unknown>;

  // ---- 6. Describe credentials --------------------------------------------
  /**
   * Return a JSON-schema-like object describing what credential
   * fields this connector needs (e.g. apiKey, accessKey/secretKey).
   */
  abstract describeCredentials(): Record<string, unknown>;
}

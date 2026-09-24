/**
 * Data models shared by every connector in the platform.
 *
 * Asset       - a normalized representation of any discovered resource
 *               (an EC2 instance, an Okta user, a Jira ticket, etc).
 * SyncResult  - the outcome of running a connector's sync() method.
 *
 * Mirrors Python models.py 1:1: same field names on the wire, same
 * defaults, same coercion behaviour. Do not rename fields here without
 * renaming them in models.py in the same PR.
 */

import { z } from "zod";

// ---- AssetType ------------------------------------------------------------

/**
 * Coarse category for a discovered asset. Extend as new connectors
 * introduce new kinds of resources.
 */
export const AssetTypeSchema = z.enum([
  "compute",
  "storage",
  "identity",
  "network",
  "ticket",
  "detection",
  "other",
]);

export type AssetType = z.infer<typeof AssetTypeSchema>;

/**
 * Member-style access mirroring Python's `class AssetType(str, Enum)`,
 * so connector authors can write `AssetType.COMPUTE` exactly as they do
 * in Python. Values are plain strings, matching Python's str-Enum.
 */
export const AssetType = {
  COMPUTE: "compute",
  STORAGE: "storage",
  IDENTITY: "identity",
  NETWORK: "network",
  TICKET: "ticket",
  DETECTION: "detection",
  OTHER: "other",
} as const satisfies Record<string, AssetType>;

// ---- Asset ----------------------------------------------------------------

/**
 * A single normalized resource discovered by a connector.
 *
 * Every connector must translate whatever it finds (an S3 bucket, an
 * Okta user, a Jira issue...) into this shape before pushing it to the
 * platform's asset service.
 */
export const Asset = z.object({
  id: z.string().describe("Stable unique ID, scoped to the source system"),
  source: z.string().describe("Name of the connector/source, e.g. 'aws', 'okta'"),
  type: AssetTypeSchema.describe("Coarse category of the asset"),
  name: z.string().describe("Human-readable name"),
  raw: z
    .record(z.string(), z.unknown())
    .default({})
    .describe("Original, unnormalized payload"),
  // z.coerce.date() so ISO-8601 strings off the wire parse the same way
  // pydantic coerces them. Plain z.date() would reject JSON input.
  discovered_at: z.coerce.date().default(() => new Date()),
  tags: z.record(z.string(), z.string()).default({}),
});

export type Asset = z.infer<typeof Asset>;

// ---- SyncStatus -----------------------------------------------------------

export const SyncStatusSchema = z.enum(["success", "partial", "failed"]);

export type SyncStatus = z.infer<typeof SyncStatusSchema>;

export const SyncStatus = {
  SUCCESS: "success",
  PARTIAL: "partial",
  FAILED: "failed",
} as const satisfies Record<string, SyncStatus>;

// ---- SyncResult -----------------------------------------------------------

/** Outcome of a single connector sync run. */
export const SyncResult = z.object({
  connector: z.string().describe("Name of the connector that ran"),
  status: SyncStatusSchema,
  assets_discovered: z.number().int().nonnegative().default(0),
  assets_pushed: z.number().int().nonnegative().default(0),
  errors: z.array(z.string()).default([]),
  started_at: z.coerce.date(),
  finished_at: z.coerce.date().default(() => new Date()),
});

export type SyncResult = z.infer<typeof SyncResult>;

/**
 * Equivalent of Python's `SyncResult.duration_seconds` property.
 * Exposed as a free function because zod infers plain objects, which
 * cannot carry getters.
 */
export function durationSeconds(result: SyncResult): number {
  return (result.finished_at.getTime() - result.started_at.getTime()) / 1000;
}
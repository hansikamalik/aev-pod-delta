/**
 * Data models shared by every connector in the platform.
 *
 * Asset      - a normalized representation of any discovered resource
 *              (an EC2 instance, an Okta user, a Jira ticket, etc).
 * SyncResult - the outcome of running a connector's sync() method.
 *
 * Mirrors the Python models.py shape 1:1 (AssetType, Asset, SyncStatus, SyncResult).
 */
import { z } from "zod";

export const AssetType = z.enum([
  "compute",
  "storage",
  "identity",
  "network",
  "ticket",
  "detection",
  "other",
]);
export type AssetType = z.infer<typeof AssetType>;

export const Asset = z.object({
  id: z.string().describe("Stable unique ID, scoped to the source system"),
  source: z.string().describe("Name of the connector/source, e.g. 'aws', 'okta'"),
  type: AssetType.describe("Coarse category of the asset"),
  name: z.string().describe("Human-readable name"),
  raw: z.record(z.string(), z.unknown()).default({}).describe("Original, unnormalized payload"),
  discoveredAt: z.date().default(() => new Date()),
  tags: z.record(z.string(), z.string()).default({}),
});
export type Asset = z.infer<typeof Asset>;

export const SyncStatus = z.enum(["success", "partial", "failed"]);
export type SyncStatus = z.infer<typeof SyncStatus>;

export const SyncResult = z.object({
  connector: z.string().describe("Name of the connector that ran"),
  status: SyncStatus,
  assetsDiscovered: z.number().int().default(0),
  assetsPushed: z.number().int().default(0),
  errors: z.array(z.string()).default([]),
  startedAt: z.date(),
  finishedAt: z.date().default(() => new Date()),
});
export type SyncResult = z.infer<typeof SyncResult>;

export function durationSeconds(result: SyncResult): number {
  return (result.finishedAt.getTime() - result.startedAt.getTime()) / 1000;
}

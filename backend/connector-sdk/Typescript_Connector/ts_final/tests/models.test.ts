
import { describe, expect, it } from "vitest";
import {
  Asset,
  AssetType,
  SyncResult,
  SyncStatus,
  durationSeconds,
} from "../src/models.js";

describe("Asset model", () => {
  it("parses a valid asset", () => {
    const asset = Asset.parse({
      id: "i-0abc123",
      source: "sample",
      type: AssetType.COMPUTE,
      name: "web-server-1",
    });

    expect(asset.id).toBe("i-0abc123");
    expect(asset.source).toBe("sample");
    expect(asset.type).toBe("compute");
    expect(asset.name).toBe("web-server-1");
  });

  it("applies Python-compatible defaults", () => {
    const asset = Asset.parse({
      id: "test-1",
      source: "sample",
      type: "compute",
      name: "test",
    });

    expect(asset.raw).toEqual({});
    expect(asset.tags).toEqual({});
    expect(asset.discovered_at).toBeInstanceOf(Date);
  });

  it("accepts an ISO datetime for discovered_at", () => {
    const asset = Asset.parse({
      id: "test-1",
      source: "sample",
      type: "compute",
      name: "test",
      discovered_at: "2026-09-23T05:00:00.000Z",
    });

    expect(asset.discovered_at).toBeInstanceOf(Date);
    expect(asset.discovered_at.toISOString()).toBe(
      "2026-09-23T05:00:00.000Z",
    );
  });

  it("rejects an invalid asset type", () => {
    expect(() =>
      Asset.parse({
        id: "test-1",
        source: "sample",
        type: "invalid",
        name: "test",
      }),
    ).toThrow();
  });

  it("supports all Python AssetType values", () => {
    const values = [
      AssetType.COMPUTE,
      AssetType.STORAGE,
      AssetType.IDENTITY,
      AssetType.NETWORK,
      AssetType.TICKET,
      AssetType.DETECTION,
      AssetType.OTHER,
    ];

    expect(values).toEqual([
      "compute",
      "storage",
      "identity",
      "network",
      "ticket",
      "detection",
      "other",
    ]);
  });
});

describe("SyncResult model", () => {
  it("parses a successful sync result", () => {
    const result = SyncResult.parse({
      connector: "sample",
      status: SyncStatus.SUCCESS,
      assets_discovered: 3,
      assets_pushed: 3,
      errors: [],
      started_at: "2026-09-23T05:00:00.000Z",
      finished_at: "2026-09-23T05:00:02.500Z",
    });

    expect(result.connector).toBe("sample");
    expect(result.status).toBe("success");
    expect(result.assets_discovered).toBe(3);
    expect(result.assets_pushed).toBe(3);
    expect(result.errors).toEqual([]);
  });

  it("applies SyncResult defaults", () => {
    const result = SyncResult.parse({
      connector: "sample",
      status: "success",
      started_at: "2026-09-23T05:00:00.000Z",
    });

    expect(result.assets_discovered).toBe(0);
    expect(result.assets_pushed).toBe(0);
    expect(result.errors).toEqual([]);
    expect(result.finished_at).toBeInstanceOf(Date);
  });

  it("rejects an invalid sync status", () => {
    expect(() =>
      SyncResult.parse({
        connector: "sample",
        status: "invalid",
        started_at: "2026-09-23T05:00:00.000Z",
      }),
    ).toThrow();
  });

  it("calculates duration_seconds like Python", () => {
    const result = SyncResult.parse({
      connector: "sample",
      status: "success",
      started_at: "2026-09-23T05:00:00.000Z",
      finished_at: "2026-09-23T05:00:02.500Z",
    });

    expect(durationSeconds(result)).toBe(2.5);
  });
});

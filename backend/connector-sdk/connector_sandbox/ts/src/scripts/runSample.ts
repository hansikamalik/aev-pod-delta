/**
 * Docker image entrypoint: runs SampleConnector end to end with no network
 * and no credentials, so `docker run <image>` proves the image works with
 * a single command. Exits 0 on SyncStatus.SUCCESS, 1 otherwise.
 */
import { SampleConnector } from "../sampleConnector.js";
import { SyncStatus } from "../models.js";

const result = await new SampleConnector().sync();
console.log(JSON.stringify(result, null, 2));
process.exit(result.status === SyncStatus.SUCCESS ? 0 : 1);

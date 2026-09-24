\# Connector SDK (TypeScript)



TypeScript scaffold of the Python Connector SDK. Method names, models, and wire field names match the Python implementation so a connector written here stays interchangeable with the Python contract.



This README covers \*\*getting the project running\*\*. For connector semantics, the six-method contract, asset/sync models, config and credential schemas, and how to author a real source (AWS, Okta, Splunk, and so on), \*\*read the Python Connector SDK documentation\*\*. Treat that as the source of truth; this package is a revival of the same scaffold, not a second spec.



\## Requirements



\- Node.js 18 or later

\- npm (ships with Node.js)



\## Startup



From the project root:



```bash

npm install

```



Build the library:



```bash

npm run build

```



Compiled output and type declarations land in `dist/`.



Run the tests (parity checks against the Python sample connector):



```bash

npm test

```



Lint:



```bash

npm run lint

```



\## Try the sample connector



`SampleConnector` is an in-memory reference implementation (same fixture rows as Python `sample\_connector.py`). After `npm run build`, you can exercise it from a small script:



```ts

import { SampleConnector } from "./dist/index.js";



const connector = new SampleConnector();



const healthy = await connector.checkHealth();

const assets = await connector.discover();

const result = await connector.sync();



console.log({ healthy, assets, result });

```



Save that as an ESM file (for example `try-sample.mjs`) next to `dist/` and run `node try-sample.mjs` after `npm run build`. For TypeScript sources without a compile step, use a NodeNext-compatible runner such as `tsx`.



Pass `true` to the constructor (`new SampleConnector(true)`) to simulate ingest/health failure, matching the Python sample.



\## Project layout



| Path | Role |

| --- | --- |

| `src/connector.ts` | Abstract `Connector`: `discover`, `ingest`, `sync`, `checkHealth`, `describeConfig`, `describeCredentials` |

| `src/models.ts` | `Asset`, `AssetType`, `SyncResult`, `SyncStatus` (Zod; same field names as Python) |

| `src/sampleConnector.ts` | Working example against fake source data |

| `src/index.ts` | Public exports |

| `tests/` | Vitest coverage of models, default `sync()`, and sample connector |



\## Writing a connector



1\. Extend `Connector`.

2\. Set `name` (for example `"aws"`).

3\. Implement the five abstract methods. Override `sync()` only if you need custom batching, retries, or incremental behavior; the default is discover → ingest with `success` / `partial` / `failed`.

4\. Map source records into `Asset.parse({ ... })` so validation matches the Python models.



Copy `src/sampleConnector.ts` as a starting point. \*\*Do not rename wire fields\*\* without changing the Python models in the same change.



\## Further reading



For the full contract, authoring guide, config/credential JSON Schema conventions, and platform ingest behavior, \*\*use the Python Connector SDK documents\*\*. This TypeScript tree is method-to-method parity with that SDK; when the two disagree, follow the Python docs and keep this scaffold in lockstep.




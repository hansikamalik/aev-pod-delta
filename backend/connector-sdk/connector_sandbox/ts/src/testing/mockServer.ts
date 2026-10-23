
/**
 * Minimal in-process mock API server. Node's built-in http module
 * only (no extra deps). Mirrors Python's testing/mock_server.py.
 */
import { createServer, Server } from "node:http";

export class MockApiServer {
  private routes: Record<string, unknown>;
  private server: Server | null = null;
  private port = 0;

  constructor(
    routes: Record<string, unknown>,
    private readonly expectedApiKey?: string,
  ) {
    this.routes = routes;
  }

  get baseUrl(): string {
    if (!this.server) {
      throw new Error("server not started -- call .start() first");
    }
    return `http://127.0.0.1:${this.port}`;
  }

  async start(): Promise<this> {
    return new Promise((resolve, reject) => {
      this.server = createServer((req, res) => {
        // Match the pathname, not the query string.
        const pathname = new URL(req.url ?? "/", this.baseUrl).pathname;

        // Authentication is optional to preserve existing test behavior.
        if (this.expectedApiKey !== undefined) {
          const authorization = req.headers.authorization;
          const expectedAuthorization = `Bearer ${this.expectedApiKey}`;

          if (authorization !== expectedAuthorization) {
            res.writeHead(401, { "Content-Type": "application/json" });
            res.end(JSON.stringify({ error: "Unauthorized" }));
            return;
          }
        }

        if (Object.prototype.hasOwnProperty.call(this.routes, pathname)) {
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(JSON.stringify(this.routes[pathname]));
        } else {
          res.writeHead(404, { "Content-Type": "application/json" });
          res.end(JSON.stringify({ error: "Not found" }));
        }
      });

      this.server.once("error", reject);

      this.server.listen(0, "127.0.0.1", () => {
        const address = this.server!.address();
        this.port = typeof address === "object" && address ? address.port : 0;
        this.server!.removeListener("error", reject);
        resolve(this);
      });
    });
  }

  async stop(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.server) {
        resolve();
        return;
      }

      this.server.close((error) => {
        if (error) reject(error);
        else {
          this.server = null;
          resolve();
        }
      });
    });
  }
}

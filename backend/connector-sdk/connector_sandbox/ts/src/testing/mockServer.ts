/**
 * Minimal in-process mock API server. Node's built-in http module
 * only (no extra deps). Mirrors Python's testing/mock_server.py.
 */
import { createServer, Server } from "node:http";

export class MockApiServer {
  private routes: Record<string, unknown>;
  private server: Server | null = null;
  private port = 0;

  constructor(routes: Record<string, unknown>) {
    this.routes = routes;
  }

  get baseUrl(): string {
    if (!this.server) throw new Error("server not started -- call .start() first");
    return `http://127.0.0.1:${this.port}`;
  }

  async start(): Promise<this> {
    return new Promise((resolve) => {
      this.server = createServer((req, res) => {
        const path = req.url ?? "";
        if (Object.prototype.hasOwnProperty.call(this.routes, path)) {
          const body = JSON.stringify(this.routes[path]);
          res.writeHead(200, { "Content-Type": "application/json" });
          res.end(body);
        } else {
          res.writeHead(404);
          res.end();
        }
      });
      this.server.listen(0, "127.0.0.1", () => {
        const address = this.server!.address();
        this.port = typeof address === "object" && address ? address.port : 0;
        resolve(this);
      });
    });
  }

  async stop(): Promise<void> {
    return new Promise((resolve) => {
      if (this.server) this.server.close(() => resolve());
      else resolve();
    });
  }
}

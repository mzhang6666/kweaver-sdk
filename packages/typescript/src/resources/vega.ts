import {
  vegaHealth,
  listVegaCatalogs,
  getVegaCatalog,
  createVegaCatalog,
  updateVegaCatalog,
  deleteVegaCatalogs,
  vegaCatalogHealthStatus,
  testVegaCatalogConnection,
  discoverVegaCatalog,
  listVegaCatalogResources,
  listVegaResources,
  getVegaResource,
  queryVegaResourceData,
  listVegaConnectorTypes,
  getVegaConnectorType,
  listVegaDiscoverTasks,
} from "../api/vega.js";
import type { ClientContext } from "../client.js";

function unwrapArray(raw: string): unknown[] {
  const parsed = JSON.parse(raw) as unknown;
  if (Array.isArray(parsed)) return parsed;
  if (parsed && typeof parsed === "object") {
    const obj = parsed as Record<string, unknown>;
    const items = obj.entries ?? obj.data ?? obj.records;
    if (Array.isArray(items)) return items;
  }
  return [];
}

export class VegaResource {
  constructor(private readonly ctx: ClientContext) {}

  // ── Health ──────────────────────────────────────────────────────────────────

  async health(): Promise<unknown> {
    const raw = await vegaHealth(this.ctx.base());
    return JSON.parse(raw);
  }

  // ── Catalogs ────────────────────────────────────────────────────────────────

  async listCatalogs(opts: { status?: string; limit?: number; offset?: number } = {}): Promise<unknown[]> {
    const raw = await listVegaCatalogs({ ...this.ctx.base(), ...opts });
    return unwrapArray(raw);
  }

  async getCatalog(id: string): Promise<unknown> {
    const raw = await getVegaCatalog({ ...this.ctx.base(), id });
    return JSON.parse(raw);
  }

  async createCatalog(data: {
    name: string;
    connector_type: string;
    connector_config: Record<string, unknown>;
    tags?: string[];
    description?: string;
  }): Promise<unknown> {
    const raw = await createVegaCatalog({ ...this.ctx.base(), body: JSON.stringify(data) });
    return JSON.parse(raw);
  }

  async updateCatalog(id: string, body: string): Promise<unknown> {
    const raw = await updateVegaCatalog({ ...this.ctx.base(), id, body });
    return raw ? JSON.parse(raw) : {};
  }

  async deleteCatalogs(ids: string): Promise<unknown> {
    const raw = await deleteVegaCatalogs({ ...this.ctx.base(), ids });
    return raw ? JSON.parse(raw) : {};
  }

  async catalogHealthStatus(ids: string): Promise<unknown> {
    const raw = await vegaCatalogHealthStatus({ ...this.ctx.base(), ids });
    return JSON.parse(raw);
  }

  async testCatalogConnection(id: string): Promise<unknown> {
    const raw = await testVegaCatalogConnection({ ...this.ctx.base(), id });
    return JSON.parse(raw);
  }

  async discoverCatalog(id: string, opts: { wait?: boolean } = {}): Promise<unknown> {
    const raw = await discoverVegaCatalog({ ...this.ctx.base(), id, ...opts });
    return JSON.parse(raw);
  }

  async listCatalogResources(
    id: string,
    opts: { category?: string; limit?: number; offset?: number } = {},
  ): Promise<unknown[]> {
    const raw = await listVegaCatalogResources({ ...this.ctx.base(), id, ...opts });
    return unwrapArray(raw);
  }

  // ── Resources ───────────────────────────────────────────────────────────────

  async listResources(opts: {
    catalogId?: string;
    category?: string;
    status?: string;
    limit?: number;
    offset?: number;
  } = {}): Promise<unknown[]> {
    const raw = await listVegaResources({ ...this.ctx.base(), ...opts });
    return unwrapArray(raw);
  }

  async getResource(id: string): Promise<unknown> {
    const raw = await getVegaResource({ ...this.ctx.base(), id });
    return JSON.parse(raw);
  }

  async queryResourceData(id: string, body: string): Promise<unknown> {
    const raw = await queryVegaResourceData({ ...this.ctx.base(), id, body });
    return JSON.parse(raw);
  }

  // ── Connector Types ─────────────────────────────────────────────────────────

  async listConnectorTypes(): Promise<unknown[]> {
    const raw = await listVegaConnectorTypes(this.ctx.base());
    return unwrapArray(raw);
  }

  async getConnectorType(type: string): Promise<unknown> {
    const raw = await getVegaConnectorType({ ...this.ctx.base(), type });
    return JSON.parse(raw);
  }

  // ── Discover Tasks ──────────────────────────────────────────────────────────

  async listDiscoverTasks(opts: { status?: string; limit?: number; offset?: number } = {}): Promise<unknown[]> {
    const raw = await listVegaDiscoverTasks({ ...this.ctx.base(), ...opts });
    return unwrapArray(raw);
  }
}

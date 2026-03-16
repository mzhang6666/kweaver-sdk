import test from "node:test";
import assert from "node:assert/strict";

import {
  listKnowledgeNetworks,
  getKnowledgeNetwork,
  createKnowledgeNetwork,
  updateKnowledgeNetwork,
  deleteKnowledgeNetwork,
  listObjectTypes,
  listRelationTypes,
  listActionTypes,
} from "../src/api/knowledge-networks.js";

const originalFetch = globalThis.fetch;

test("listKnowledgeNetworks maps query filters and headers", async () => {
  globalThis.fetch = async (input, init) => {
    const url = new URL(typeof input === "string" ? input : input.toString());
    const headers = new Headers(init?.headers);

    assert.equal(init?.method, "GET");
    assert.equal(url.pathname, "/api/ontology-manager/v1/knowledge-networks");
    assert.equal(url.searchParams.get("offset"), "5");
    assert.equal(url.searchParams.get("limit"), "20");
    assert.equal(url.searchParams.get("sort"), "name");
    assert.equal(url.searchParams.get("direction"), "asc");
    assert.equal(url.searchParams.get("name_pattern"), "incident");
    assert.equal(url.searchParams.get("tag"), "prod");
    assert.equal(headers.get("authorization"), "Bearer token-abc");
    assert.equal(headers.get("token"), "token-abc");
    assert.equal(headers.get("x-business-domain"), "bd_enterprise");
    return new Response("{\"items\":[]}", { status: 200 });
  };

  try {
    const body = await listKnowledgeNetworks({
      baseUrl: "https://dip.aishu.cn/",
      accessToken: "token-abc",
      businessDomain: "bd_enterprise",
      offset: 5,
      limit: 20,
      sort: "name",
      direction: "asc",
      name_pattern: "incident",
      tag: "prod",
    });
    assert.equal(body, "{\"items\":[]}");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("getKnowledgeNetwork maps export and stats query params", async () => {
  globalThis.fetch = async (input, init) => {
    const url = new URL(typeof input === "string" ? input : input.toString());
    assert.equal(init?.method, "GET");
    assert.equal(url.pathname, "/api/ontology-manager/v1/knowledge-networks/kn-123");
    assert.equal(url.searchParams.get("mode"), "export");
    assert.equal(url.searchParams.get("include_statistics"), "true");
    return new Response("{\"id\":\"kn-123\"}", { status: 200 });
  };

  try {
    const body = await getKnowledgeNetwork({
      baseUrl: "https://dip.aishu.cn",
      accessToken: "token-abc",
      knId: "kn-123",
      mode: "export",
      include_statistics: true,
    });
    assert.equal(body, "{\"id\":\"kn-123\"}");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("createKnowledgeNetwork maps query params and JSON body", async () => {
  globalThis.fetch = async (input, init) => {
    const url = new URL(typeof input === "string" ? input : input.toString());
    const headers = new Headers(init?.headers);
    assert.equal(init?.method, "POST");
    assert.equal(url.pathname, "/api/ontology-manager/v1/knowledge-networks");
    assert.equal(url.searchParams.get("import_mode"), "overwrite");
    assert.equal(url.searchParams.get("validate_dependency"), "false");
    assert.equal(headers.get("content-type"), "application/json");
    assert.equal(init?.body, "{\"name\":\"Network\",\"branch\":\"main\",\"base_branch\":\"\"}");
    return new Response("[{\"id\":\"kn-123\"}]", { status: 201 });
  };

  try {
    const body = await createKnowledgeNetwork({
      baseUrl: "https://dip.aishu.cn",
      accessToken: "token-abc",
      body: "{\"name\":\"Network\",\"branch\":\"main\",\"base_branch\":\"\"}",
      import_mode: "overwrite",
      validate_dependency: false,
    });
    assert.equal(body, "[{\"id\":\"kn-123\"}]");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("updateKnowledgeNetwork maps path and JSON body", async () => {
  globalThis.fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input.toString();
    const headers = new Headers(init?.headers);
    assert.equal(init?.method, "PUT");
    assert.equal(url, "https://dip.aishu.cn/api/ontology-manager/v1/knowledge-networks/kn-123");
    assert.equal(headers.get("content-type"), "application/json");
    assert.equal(init?.body, "{\"name\":\"Updated\",\"branch\":\"main\",\"base_branch\":\"\"}");
    return new Response(null, { status: 204 });
  };

  try {
    const body = await updateKnowledgeNetwork({
      baseUrl: "https://dip.aishu.cn",
      accessToken: "token-abc",
      knId: "kn-123",
      body: "{\"name\":\"Updated\",\"branch\":\"main\",\"base_branch\":\"\"}",
    });
    assert.equal(body, "");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("deleteKnowledgeNetwork maps method and path", async () => {
  globalThis.fetch = async (input, init) => {
    const url = typeof input === "string" ? input : input.toString();
    assert.equal(init?.method, "DELETE");
    assert.equal(url, "https://dip.aishu.cn/api/ontology-manager/v1/knowledge-networks/kn-123");
    return new Response(null, { status: 204 });
  };

  try {
    await deleteKnowledgeNetwork({
      baseUrl: "https://dip.aishu.cn",
      accessToken: "token-abc",
      knId: "kn-123",
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("listObjectTypes maps path and params", async () => {
  globalThis.fetch = async (input) => {
    const url = new URL(typeof input === "string" ? input : input.toString());
    assert.equal(url.pathname, "/api/ontology-manager/v1/knowledge-networks/kn-1/object-types");
    assert.equal(url.searchParams.get("branch"), "main");
    assert.equal(url.searchParams.get("limit"), "-1");
    return new Response("[{\"id\":\"ot-1\",\"name\":\"Product\"}]", { status: 200 });
  };

  try {
    const body = await listObjectTypes({
      baseUrl: "https://dip.aishu.cn",
      accessToken: "token",
      knId: "kn-1",
    });
    assert.ok(body.includes("ot-1"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("listRelationTypes maps path and params", async () => {
  globalThis.fetch = async (input) => {
    const url = new URL(typeof input === "string" ? input : input.toString());
    assert.equal(url.pathname, "/api/ontology-manager/v1/knowledge-networks/kn-1/relation-types");
    return new Response("[{\"id\":\"rt-1\",\"name\":\"Product_Inventory\"}]", { status: 200 });
  };

  try {
    const body = await listRelationTypes({
      baseUrl: "https://dip.aishu.cn",
      accessToken: "token",
      knId: "kn-1",
    });
    assert.ok(body.includes("rt-1"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("listActionTypes maps path and params", async () => {
  globalThis.fetch = async (input) => {
    const url = new URL(typeof input === "string" ? input : input.toString());
    assert.equal(url.pathname, "/api/ontology-manager/v1/knowledge-networks/kn-1/action-types");
    return new Response("[{\"id\":\"at-1\",\"name\":\"CreateOrder\"}]", { status: 200 });
  };

  try {
    const body = await listActionTypes({
      baseUrl: "https://dip.aishu.cn",
      accessToken: "token",
      knId: "kn-1",
    });
    assert.ok(body.includes("at-1"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

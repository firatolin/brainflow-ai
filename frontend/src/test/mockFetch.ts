export function mockFetch(responses: Record<string, unknown>): typeof fetch {
  return (async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === "string" ? input : input.toString();
    const key = Object.keys(responses).find((k) => url.includes(k));
    const body = key !== undefined ? responses[key] : { detail: "not mocked" };
    const ok = key !== undefined;
    const method = init?.method ?? "GET";
    if (method !== "GET" && ok && body && typeof body === "object" && "__error" in (body as object)) {
      const errBody = (body as { __error: unknown }).__error;
      return new Response(JSON.stringify(errBody), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify(body), {
      status: ok ? 200 : 404,
      headers: { "Content-Type": "application/json" },
    });
  }) as unknown as typeof fetch;
}

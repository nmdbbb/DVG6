// Client gọi FastAPI. Mọi type lấy từ schema.d.ts (sinh bằng `npm run gen:api`), không gõ tay.
import type { components, paths } from './schema';

const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

type Schemas = components['schemas'];
export type Source = Schemas['Source'];
export type Batch = Schemas['Batch'];
export type QualityCheck = Schemas['QualityCheck'];
export type QualityRun = Schemas['QualityRun'];
export type LayerTable = Schemas['LayerTable'];
export type CatalogTable = Schemas['Table'];
export type CatalogColumn = Schemas['Column'];
export type ResponseMeta = Schemas['Meta'];

type GetPath = {
  [P in keyof paths]: paths[P] extends { get: unknown } ? P : never;
}[keyof paths];

type JsonOf<P extends GetPath> = paths[P]['get'] extends {
  responses: { 200: { content: { 'application/json': infer R } } };
}
  ? R
  : never;

type QueryOf<P extends GetPath> = paths[P]['get'] extends { parameters: { query?: infer Q } }
  ? Q
  : never;

type PathOf<P extends GetPath> = paths[P]['get'] extends { parameters: { path: infer A } }
  ? A
  : never;

export interface Request<P extends GetPath> {
  query?: QueryOf<P>;
  path?: PathOf<P>;
}

export function buildUrl<P extends GetPath>(path: P, req: Request<P> = {}): string {
  let url = path as string;
  for (const [k, v] of Object.entries((req.path ?? {}) as Record<string, string>)) {
    url = url.replace(`{${k}}`, encodeURIComponent(v));
  }
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries((req.query ?? {}) as Record<string, unknown>)) {
    if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
  }
  const q = qs.toString();
  return `${BASE}${url}${q ? `?${q}` : ''}`;
}

export async function apiGet<P extends GetPath>(path: P, req: Request<P> = {}): Promise<JsonOf<P>> {
  const res = await fetch(buildUrl(path, req));
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText} — ${body.slice(0, 200)}`);
  }
  return res.json() as Promise<JsonOf<P>>;
}

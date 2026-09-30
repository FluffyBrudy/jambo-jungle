export const DEFAULT_API_BASE = "https://gametools-blush.vercel.app";
export const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;

export function apiBase(): string {
  const raw = process.env.GAMETOOLS_API ?? DEFAULT_API_BASE;
  return raw.replace(/\/+$/, "");
}

export class CliError extends Error {
  code: number;
  constructor(message: string, code: number) {
    super(message);
    this.name = "CliError";
    this.code = code;
  }
}

export interface PresetSummary {
  id: string;
  name: string;
  badge: string;
  description: string;
  category: string | null;
}

async function getJson(url: string): Promise<unknown> {
  let res: Response;
  try {
    res = await fetch(url);
  } catch (e) {
    throw new CliError(
      `cannot reach API at ${url}: ${(e as Error).message}`,
      5,
    );
  }
  if (!res.ok) throw new CliError(`API error ${res.status} on GET ${url}`, 5);
  return res.json();
}

export async function health(base: string = apiBase()): Promise<unknown> {
  return getJson(`${base}/api/v1/tileset/health`);
}

export async function listPresets(
  base: string = apiBase(),
): Promise<PresetSummary[]> {
  const data = (await getJson(`${base}/api/v1/tileset/presets`)) as {
    presets?: PresetSummary[];
  };
  if (!Array.isArray(data.presets))
    throw new CliError("unexpected preset list response", 5);
  return data.presets;
}

export async function getPreset(
  id: string,
  base: string = apiBase(),
): Promise<unknown> {
  return getJson(`${base}/api/v1/tileset/presets/${encodeURIComponent(id)}`);
}

export type OutFormat = "png" | "jpeg";

export interface RemasterOptions {
  theme?: string;
  tileSize?: number;
  format?: OutFormat;
  excludedTileIndices?: number[];
  selectedTileIndices?: number[];
  force?: boolean;
}

export interface RemasterResult {
  target: string;
  theme: string;
  dimensions: string;
  bytes: number;
}

export async function remaster(
  srcPath: string,
  targetPath: string,
  opts: RemasterOptions = {},
  base: string = apiBase(),
): Promise<RemasterResult> {
  const src = Bun.file(srcPath);
  if (!(await src.exists()))
    throw new CliError(`source not found: ${srcPath}`, 3);
  if (src.size === 0) throw new CliError(`source is empty: ${srcPath}`, 3);
  if (src.size > MAX_UPLOAD_BYTES) {
    throw new CliError(
      `source is ${(src.size / 1048576).toFixed(1)} MB; API limit is 8 MB`,
      3,
    );
  }
  if (!opts.force && (await Bun.file(targetPath).exists())) {
    throw new CliError(
      `target exists, refusing to overwrite: ${targetPath}\npass --force to overwrite`,
      4,
    );
  }

  const form = new FormData();
  const filename = srcPath.split("/").pop() || "image.png";
  form.set("image", src, filename);
  if (opts.theme) form.set("theme", opts.theme);
  if (opts.tileSize !== undefined) form.set("tileSize", String(opts.tileSize));
  form.set("format", opts.format ?? "png");
  if (opts.excludedTileIndices?.length)
    form.set("excludedTileIndices", JSON.stringify(opts.excludedTileIndices));
  if (opts.selectedTileIndices?.length)
    form.set("selectedTileIndices", JSON.stringify(opts.selectedTileIndices));

  let res: Response;
  try {
    res = await fetch(`${base}/api/v1/tileset/remaster`, {
      method: "POST",
      body: form,
    });
  } catch (e) {
    throw new CliError(
      `cannot reach API at ${base}: ${(e as Error).message}`,
      5,
    );
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let detail = text.slice(0, 300);
    try {
      const parsed = JSON.parse(text) as { detail?: unknown };
      if (typeof parsed.detail === "string" && parsed.detail)
        detail = parsed.detail;
    } catch {
      // keep raw text
    }
    throw new CliError(
      `API error ${res.status}: ${detail || res.statusText}`,
      5,
    );
  }

  const bytes = new Uint8Array(await res.arrayBuffer());
  await Bun.write(targetPath, bytes);
  return {
    target: targetPath,
    theme: res.headers.get("x-remaster-theme") ?? opts.theme ?? "unknown",
    dimensions: res.headers.get("x-remaster-dimensions") ?? "?",
    bytes: bytes.length,
  };
}

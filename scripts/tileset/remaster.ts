import path from "node:path";
import { parseArgs } from "node:util";
import {
  apiBase,
  CliError,
  listPresets,
  remaster,
  type OutFormat,
} from "./api.ts";

export const SCRIPTS_DIR = path.dirname(import.meta.dir);
export const IMAGES_DIR = path.join(SCRIPTS_DIR, "images");
const INPUT_CANDIDATES = ["input.png", "input.jpg", "input.jpeg", "input.webp"];

export const PRESET_IDS = [
  "spring_blossom",
  "summer_lush",
  "autumn_harvest",
  "winter_frost",
  "forest_peak",
  "desert_scorched",
  "toxic_swamp",
  "abyssal_trench",
  "celestial_gold",
  "crystal_cavern",
  "dark_blight",
  "cyber_neon",
  "blood_moon",
] as const;

export const THEME_KEYS: Record<string, string> = {
  spring: "spring_blossom",
  summer: "summer_lush",
  autumn: "autumn_harvest",
  fall: "autumn_harvest",
  winter: "winter_frost",
};

/** Resolve a --theme value (short key or full id) or throw CliError(2). */
export function resolveTheme(raw: string): string {
  const key = raw.trim().toLowerCase();
  if (THEME_KEYS[key]) return THEME_KEYS[key];
  if ((PRESET_IDS as readonly string[]).includes(key)) return key;
  throw new CliError(
    `unknown theme "${raw}"\nvalid keys: ${Object.keys(THEME_KEYS).join(", ")}\nvalid ids: ${PRESET_IDS.join(", ")}`,
    2,
  );
}

export interface RunDefaults {
  theme?: string;
  tileSize?: number;
  format?: OutFormat;
}

const HELP = `usage:
  remaster.ts [options] [src] [target]

args:
  src       source tileset (absolute, or relative to scripts/).
            default: images/input.png (.jpg/.jpeg/.webp also tried)
  target    output path (absolute, or relative to scripts/).
            default: images/input-<theme-id>.png
            refuses to overwrite unless --force is given

options:
  --theme <key|id>    spring | summer | autumn | winter (fall works too),
                      or any full preset id:
                      ${PRESET_IDS.join(", ")}
                      (default: autumn_harvest)
  --tile-size <n>     tile grid size 2-64 (default: 16)
  --format <png|jpeg> output format (default: png)
  --excluded <list>   comma-separated locked tile indices, e.g. 0,1,2
  --selected <list>   comma-separated indices; only these remaster
  --force             allow overwriting an existing target
  --api-base <url>    override API base (or GAMETOOLS_API env)
  --list              print available preset ids and exit
  -h, --help          this help

exit codes: 0 ok · 2 bad usage · 3 source missing · 4 target exists · 5 API error · 1 unexpected

examples:
  bun scripts/tileset/remaster.ts --theme autumn assets/tiles/in.png assets/tiles/in-autumn.png
  bun scripts/tileset/remaster.ts --theme toxic_swamp in.png out.png --tile-size 32
  bun scripts/tileset/remaster.ts --list`;

function report(e: unknown): number {
  if (e instanceof CliError) {
    console.error(`error: ${e.message}`);
    return e.code;
  }
  console.error(`error: ${(e as Error)?.message ?? e}`);
  return 1;
}

function parseIntList(
  raw: string | undefined,
  flag: string,
): number[] | undefined {
  if (raw === undefined) return undefined;
  const nums = raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map(Number);
  if (nums.length === 0 || nums.some((n) => !Number.isInteger(n) || n < 0)) {
    throw new CliError(
      `--${flag} must be comma-separated non-negative ints`,
      2,
    );
  }
  return nums;
}

export function resolvePath(p: string): string {
  return path.isAbsolute(p) ? p : path.join(SCRIPTS_DIR, p);
}

async function resolveSrc(arg: string | undefined): Promise<string> {
  if (arg) {
    const full = resolvePath(arg);
    if (!(await Bun.file(full).exists()))
      throw new CliError(`source not found: ${full}`, 3);
    return full;
  }
  for (const name of INPUT_CANDIDATES) {
    const full = path.join(IMAGES_DIR, name);
    if (await Bun.file(full).exists()) return full;
  }
  throw new CliError(
    `no source given and none of ${INPUT_CANDIDATES.map((n) => `images/${n}`).join(", ")} exists\n` +
      `pass a path or drop an input file in scripts/images/`,
    3,
  );
}

function resolveTarget(
  arg: string | undefined,
  theme: string,
  format: OutFormat,
): string {
  if (arg) return resolvePath(arg);
  return path.join(
    IMAGES_DIR,
    `input-${theme}.${format === "jpeg" ? "jpg" : "png"}`,
  );
}

export async function run(
  argv: string[],
  defaults: RunDefaults = {},
): Promise<number> {
  let values: Record<string, string | boolean | undefined>;
  let positionals: string[];
  try {
    ({ values, positionals } = parseArgs({
      args: argv,
      allowPositionals: true,
      options: {
        theme: { type: "string" },
        "tile-size": { type: "string" },
        format: { type: "string" },
        excluded: { type: "string" },
        selected: { type: "string" },
        force: { type: "boolean", default: false },
        "api-base": { type: "string" },
        list: { type: "boolean", default: false },
        help: { type: "boolean", default: false, short: "h" },
      },
    }));
  } catch (e) {
    console.error(`bad arguments: ${(e as Error).message}\n\n${HELP}`);
    return 2;
  }
  if (values.help) {
    console.log(HELP);
    return 0;
  }

  const base = (values["api-base"] as string | undefined) ?? apiBase();

  if (values.list) {
    try {
      for (const p of await listPresets(base))
        console.log(`${p.id}  —  ${p.name}`);
      return 0;
    } catch (e) {
      return report(e);
    }
  }

  try {
    const theme = resolveTheme(
      (values.theme as string | undefined) ??
        defaults.theme ??
        "autumn_harvest",
    );
    const tileSizeRaw =
      (values["tile-size"] as string | undefined) ??
      (defaults.tileSize !== undefined ? String(defaults.tileSize) : undefined);
    let tileSize: number | undefined;
    if (tileSizeRaw !== undefined) {
      tileSize = Number(tileSizeRaw);
      if (!Number.isInteger(tileSize) || tileSize < 2 || tileSize > 64) {
        throw new CliError("--tile-size must be an int between 2 and 64", 2);
      }
    }
    const formatRaw = (
      ((values.format as string | undefined) ??
        defaults.format ??
        "png") as string
    ).toLowerCase();
    if (formatRaw !== "png" && formatRaw !== "jpeg")
      throw new CliError('--format must be "png" or "jpeg"', 2);
    const format = formatRaw as OutFormat;
    const excluded = parseIntList(
      values.excluded as string | undefined,
      "excluded",
    );
    const selected = parseIntList(
      values.selected as string | undefined,
      "selected",
    );

    const [srcArg, targetArg] = positionals;
    const srcPath = await resolveSrc(srcArg);
    const targetPath = resolveTarget(targetArg, theme, format);
    const result = await remaster(
      srcPath,
      targetPath,
      {
        theme,
        tileSize,
        format,
        excludedTileIndices: excluded,
        selectedTileIndices: selected,
        force: values.force as boolean,
      },
      base,
    );
    console.log(
      `ok: ${result.target}\n    ${result.dimensions}, theme ${result.theme}, ${(result.bytes / 1024).toFixed(1)} KB`,
    );
    return 0;
  } catch (e) {
    return report(e);
  }
}

if (import.meta.main) process.exit(await run(Bun.argv.slice(2), {}));

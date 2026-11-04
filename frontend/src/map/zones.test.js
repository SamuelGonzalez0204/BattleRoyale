import { describe, expect, test } from "vitest";
import { readFileSync } from "node:fs";
import { fallenWeightAt, isPointFallen, normalizeFallen, partitionRegions, regionOwnerAt } from "./zones.js";
import { baseKey, kitScale } from "./kits.js";
import { createTerrain } from "./terrain.js";

const DATA = JSON.parse(readFileSync(new URL("../../public/mapa/map-data.json", import.meta.url), "utf8"));
const { regions } = DATA;
const region = (id) => regions.find((r) => r.id === id);

describe("regionOwnerAt", () => {
  test("region centers belong to their region", () => {
    for (const r of regions) expect(regionOwnerAt(regions, ...r.center)).toBe(r.id);
  });
  test("outside every circle there is no owner", () => {
    expect(regionOwnerAt(regions, 1000, 1000)).toBeNull();
  });
  test("the muralla/cumbres overlap is split by relative depth", () => {
    expect(regionOwnerAt(regions, 0, -150)).toBe("muralla");
    expect(regionOwnerAt(regions, 0, -175)).toBe("cumbres");
  });
});

describe("fallen helpers", () => {
  test("normalizeFallen keeps order, drops unknown and duplicate ids", () => {
    expect(normalizeFallen(["bahia", "nope", "campos", "bahia", 3], regions)).toEqual(["bahia", "campos"]);
    expect(normalizeFallen(null, regions)).toEqual([]);
  });
  test("isPointFallen and fallenWeightAt", () => {
    const fallen = ["bahia"], b = region("bahia");
    expect(isPointFallen(regions, fallen, ...b.center)).toBe(true);
    expect(isPointFallen(regions, fallen, ...region("plaza").center)).toBe(false);
    expect(fallenWeightAt(regions, fallen, ...b.center)).toBe(1);
    expect(fallenWeightAt(regions, [], ...b.center)).toBe(0);
    const edge = fallenWeightAt(regions, fallen, b.center[0], b.center[1] + b.radius * 0.95);
    expect(edge).toBeGreaterThan(0); expect(edge).toBeLessThan(1);
  });
  test("partitionRegions", () => {
    const { fallen, standing } = partitionRegions(regions, ["campos", "bahia"]);
    expect(fallen.map((r) => r.id)).toEqual(["campos", "bahia"]);
    expect(standing).toHaveLength(regions.length - 2);
  });
  test("every backend zone id exists in the map", () => {
    for (const id of ["bahia", "campos", "bosque", "cementerio", "muralla", "plaza", "cumbres"]) expect(region(id)).toBeDefined();
  });
});

describe("kits and terrain", () => {
  test("kit scales", () => {
    expect(baseKey("td/detail-crystal#glow")).toBe("td/detail-crystal");
    expect(kitScale("town/fountain-round-detail")).toBeCloseTo(1.5 * 2.6);
    expect(kitScale("proc/wheat")).toBe(1);
  });
  test("height field is deterministic, the plaza is land and the far sea is water", () => {
    const a = createTerrain(DATA), b = createTerrain(DATA);
    for (const [x, z] of [[0, 0], [8, 132], [-148, 8], [0, -192]]) expect(a.H(x, z)).toBe(b.H(x, z));
    expect(a.H(0, 0)).toBeGreaterThan(1);
    expect(a.H(290, 290)).toBeLessThan(0);
  });
});

import { describe, expect, test } from "vitest";
import {
  apiErrorText, clampSpend, formatCountdown, hearts, isUuid, reasonText, sections, statusLine,
  tacticLabel, tacticShares, viewerConfig, voteWeight,
} from "./view.js";

const champions = [
  { faction_slug: "gremio", faction_name: "Gremio del Comercio" },
  { faction_slug: "orden", faction_name: "Orden de la Muralla" },
];
const base = {
  total_rounds: 7, champions,
  zones: [{ id: "bahia", name: "Bahía del Gremio" }, { id: "campos", name: "Campos y Molinos" }],
  seal: { options: [], selected: null, deadline: null, can_choose: false },
};

describe("reasonText", () => {
  test("below_gap names the wounded faction", () => {
    expect(reasonText(base, { reason: "below_gap", wounded_faction_slug: "orden" })).toMatch(/^Orden de la Muralla quedó por debajo del 85 %/);
  });
  test("adds the elimination", () => {
    expect(reasonText(base, { reason: "below_gap", wounded_faction_slug: "orden", eliminated_faction_slug: "orden" })).toMatch(/queda fuera/);
  });
  test("other reasons and unknown", () => {
    expect(reasonText(base, { reason: "within_gap" })).toMatch(/nadie resulta herido/);
    expect(reasonText(base, { reason: "final_round" })).toMatch(/Arena/);
    expect(reasonText(base, { reason: "no_contenders" })).toMatch(/sin heridas/);
    expect(reasonText(base, { reason: "zzz" })).toBe("Ronda resuelta.");
    expect(reasonText(base, null)).toBe("");
  });
});

describe("small formatters", () => {
  test("hearts", () => {
    expect(hearts(0, 3)).toEqual([true, true, true]);
    expect(hearts(2, 3)).toEqual([true, false, false]);
    expect(hearts(5, 3)).toEqual([false, false, false]);
  });
  test("formatCountdown", () => {
    expect(formatCountdown(0)).toBeNull();
    expect(formatCountdown(-5)).toBeNull();
    expect(formatCountdown(12_000)).toBe("12 s");
    expect(formatCountdown(249_000)).toBe("4 min 09 s");
    expect(formatCountdown(2 * 3600_000 + 5 * 60_000)).toBe("2 h 05 min");
    expect(formatCountdown(26 * 3600_000)).toBe("1 d 2 h");
  });
  test("spend and weight", () => {
    expect(clampSpend(80, 1000)).toBe(50);
    expect(clampSpend(30, 12)).toBe(12);
    expect(clampSpend("abc", 10)).toBe(0);
    expect(clampSpend(-3, 10)).toBe(0);
    expect(voteWeight(10)).toBe(11);
    expect(voteWeight(99)).toBe(51);
  });
  test("tactic labels and shares", () => {
    expect(tacticLabel("astucia")).toBe("Astucia");
    expect(tacticLabel(null)).toBe("Sin táctica");
    expect(tacticShares({ ataque: 3, defensa: 1, astucia: 0 }).map((s) => s.pct)).toEqual([75, 25, 0]);
    expect(tacticShares(null).every((s) => s.pct === 0)).toBe(true);
  });
  test("uuid and error text", () => {
    expect(isUuid("0b7c5c1e-1d2a-4b8f-9a10-3f0e6c2d9a11")).toBe(true);
    expect(isUuid("abc")).toBe(false);
    expect(apiErrorText({ status: 429, message: "x" })).toMatch(/Demasiadas/);
    expect(apiErrorText({ status: 409, message: "Ya votaste" })).toBe("No se pudo: Ya votaste");
    expect(apiErrorText(new Error("boom"))).toBe("boom");
  });
});

describe("viewerConfig and sections", () => {
  test("active event forces colapso, marks fallen zones and focuses the current zone", () => {
    const st = { ...base, status: "active", round_number: 2, current_zone: "campos", fallen_zones: ["bahia"], current_duel: { id: "d" }, last_round: { reason: "within_gap" } };
    expect(viewerConfig(st, "construccion")).toEqual({ phase: "colapso", fallen: ["bahia"], focus: "campos" });
    expect(sections(st)).toMatchObject({ duel: true, champions: true, lastRound: true, sponsor: false, intro: false, sealPicker: false });
    expect(statusLine(st)).toBe("Ronda 2 de 7 · Campos y Molinos");
  });
  test("no event follows the world phase and shows the sponsorship", () => {
    const st = { ...base, status: "none", champions: [] };
    expect(viewerConfig(st, "convergencia")).toEqual({ phase: "convergencia", fallen: [], focus: null });
    expect(viewerConfig(st, null).phase).toBe("construccion");
    expect(sections(st)).toMatchObject({ intro: true, sponsor: true, champions: false, duel: false });
  });
  test("finished: seal picker only for who can choose", () => {
    const st = { ...base, status: "finished", fallen_zones: ["bahia", "campos"], winner: { faction_name: "x" }, seal: { ...base.seal, can_choose: true } };
    expect(sections(st)).toMatchObject({ winner: true, sealPicker: true, sealWaiting: false, sealed: false });
    expect(sections({ ...st, seal: base.seal })).toMatchObject({ sealPicker: false, sealWaiting: true });
    expect(viewerConfig(st).focus).toBe("cumbres");
  });
  test("sealed", () => {
    expect(sections({ ...base, status: "sealed", winner: { faction_name: "x" } })).toMatchObject({ sealed: true, winner: true, sealPicker: false });
  });
});

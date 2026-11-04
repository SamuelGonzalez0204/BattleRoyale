import { describe, expect, test } from "vitest";
import { clamp, distPoly, fbm, hash2, mulberry32, segX, smooth, vnoise, esc } from "./noise.js";

describe("mulberry32", () => {
  test("same seed yields the same sequence", () => {
    const a = mulberry32(20261103), b = mulberry32(20261103);
    expect(Array.from({ length: 50 }, a)).toEqual(Array.from({ length: 50 }, b));
  });
  test("values are in [0, 1) and differ across seeds", () => {
    const xs = Array.from({ length: 1000 }, mulberry32(1));
    expect(Math.min(...xs)).toBeGreaterThanOrEqual(0);
    expect(Math.max(...xs)).toBeLessThan(1);
    expect(mulberry32(2)()).not.toBe(mulberry32(1)());
  });
});

describe("noise", () => {
  test("hash2, vnoise and fbm are deterministic and bounded", () => {
    expect(hash2(3, 7)).toBe(hash2(3, 7));
    for (let i = 0; i < 200; i++) {
      const v = vnoise(i * 0.37, i * -0.21), f = fbm(i * 0.11, i * 0.07);
      expect(v).toBeGreaterThanOrEqual(0); expect(v).toBeLessThanOrEqual(1);
      expect(f).toBeGreaterThanOrEqual(0); expect(f).toBeLessThanOrEqual(1.0001);
    }
  });
  test("vnoise equals the lattice hash on integer points", () => {
    expect(vnoise(4, 9)).toBeCloseTo(hash2(4, 9), 12);
  });
  test("smooth and clamp", () => {
    expect(smooth(0, 10, -5)).toBe(0);
    expect(smooth(0, 10, 15)).toBe(1);
    expect(smooth(0, 10, 5)).toBeCloseTo(0.5, 12);
    expect(smooth(10, 0, 0)).toBe(1);
    expect(clamp(5, 0, 3)).toBe(3);
  });
});

describe("distPoly", () => {
  const line = [[0, 0], [10, 0], [10, 10]];
  test("distance, arc position and total length", () => {
    const p = distPoly(line, 5, 3);
    expect(p.d).toBeCloseTo(3); expect(p.s).toBeCloseTo(5); expect(p.len).toBeCloseTo(20);
  });
  test("closest point on the second segment", () => {
    const p = distPoly(line, 13, 6);
    expect(p.d).toBeCloseTo(3); expect(p.s).toBeCloseTo(16);
  });
  test("beyond the end clamps to the last vertex", () => {
    expect(distPoly(line, 10, 14).d).toBeCloseTo(4);
  });
});

describe("segX and esc", () => {
  test("crossing and parallel segments", () => {
    expect(segX([0, 0], [10, 10], [0, 10], [10, 0])).toEqual([5, 5]);
    expect(segX([0, 0], [10, 0], [0, 1], [10, 1])).toBeNull();
    expect(segX([0, 0], [1, 1], [5, 0], [6, -1])).toBeNull();
  });
  test("escapes HTML", () => {
    expect(esc('<a href="x">&</a>')).toBe("&lt;a href=&quot;x&quot;&gt;&amp;&lt;/a&gt;");
  });
});

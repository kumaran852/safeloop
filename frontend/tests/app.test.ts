import { describe, expect, it } from "vitest";
import { en } from "../src/i18n/en";
import { ta, taLabels } from "../src/i18n/ta";
import { qs } from "../src/services/api";
import { parseUtc } from "../src/utils/format";
import { validateReport } from "../src/utils/validate";

const ok = { workerId: "SW-0001", ward: "1", task: "Loading", region: "shoulder", severity: 7, hours: "9", shift: "Morning" };

describe("validateReport", () => {
  it("accepts a complete draft", () => expect(validateReport(ok)).toEqual({}));
  it("flags missing / out-of-range fields", () => {
    const e = validateReport({ ...ok, workerId: "", severity: 11, hours: "0", region: "" });
    expect(Object.keys(e).sort()).toEqual(["hours", "region", "severity", "workerId"]);
  });
});
describe("i18n", () => {
  it("Tamil has a non-empty translation for every English key", () => {
    for (const k of Object.keys(en)) expect((ta as Record<string, string>)[k]?.length).toBeGreaterThan(0);
  });
  it("Tamil labels cover all body regions", () => expect(Object.keys(taLabels.regions)).toHaveLength(8));
});
describe("utils", () => {
  it("builds query strings and skips empty values", () => expect(qs({ a: 1, b: "", c: undefined, d: "x" })).toBe("?a=1&d=x"));
  it("treats naive timestamps as UTC", () => expect(parseUtc("2026-01-01T00:00:00")?.toISOString()).toBe("2026-01-01T00:00:00.000Z"));
});

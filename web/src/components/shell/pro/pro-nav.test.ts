import { describe, expect, it } from "vitest";

import { activeProKey, PRO_BAR, PRO_NAV, STAFF_NAV } from "./pro-nav";

describe("the menu of a talent", () => {
  it("lights the most precise entry", () => {
    expect(activeProKey("/pro")).toBe("today");
    expect(activeProKey("/pro/agenda")).toBe("agenda");
    expect(activeProKey("/pro/agenda/arrivee/RDV-1")).toBe("agenda");
    expect(activeProKey("/pro/agenda/clients")).toBe("clients");
    expect(activeProKey("/pro/agenda/settings")).toBe("agendaSettings");
    expect(activeProKey("/pro/shop/product/new")).toBe("shop");
    expect(activeProKey("/pro/unknown")).toBeUndefined();
  });

  it("keeps appointments and the shop under the thumb", () => {
    expect(PRO_BAR).toEqual(expect.arrayContaining(["today", "agenda", "shop"]));
    expect(PRO_BAR.length).toBeLessThanOrEqual(4);
  });

  it("gives a collaborator only what she works with", () => {
    const keys = PRO_NAV.map(({ key }) => key);
    expect(keys).toEqual(expect.arrayContaining(STAFF_NAV));
    expect(STAFF_NAV).not.toContain("money");
  });
});

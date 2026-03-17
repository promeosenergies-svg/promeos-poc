/**
 * PROMEOS — E8: Action Center Flow
 * Validates the action center console loads and displays issues/actions.
 */
import { test, expect } from "@playwright/test";
import { login, screenshot, waitForPageReady, BACKEND_URL } from "./helpers.js";

test.describe("E8: Action Center Console", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("T1: Action center page loads", async ({ page }) => {
    await page.goto("/action-center");
    await waitForPageReady(page);
    await expect(page.locator("text=Une erreur est survenue")).not.toBeVisible({
      timeout: 5000,
    });
    await screenshot(page, "e8-t1-action-center");
  });

  test("T2: Action center API returns issues", async ({ request }) => {
    const r = await request.get(`${BACKEND_URL}/api/action-center/issues`, {
      headers: { "X-Org-Id": "1" },
    });
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data).toHaveProperty("total");
    expect(data).toHaveProperty("issues");
    expect(Array.isArray(data.issues)).toBe(true);
  });

  test("T3: Action center summary returns counts", async ({ request }) => {
    const r = await request.get(
      `${BACKEND_URL}/api/action-center/actions/summary`
    );
    expect(r.status()).toBe(200);
    const data = await r.json();
    expect(data).toHaveProperty("total");
    expect(data).toHaveProperty("by_status");
    expect(data).toHaveProperty("overdue_count");
  });

  test("T4: Create + resolve action flow", async ({ request }) => {
    // Create
    const r1 = await request.post(
      `${BACKEND_URL}/api/action-center/actions`,
      {
        data: {
          issue_id: "e2e_test_flow",
          domain: "compliance",
          severity: "medium",
          site_id: 1,
          issue_code: "e2e_test",
          issue_label: "E2E test action",
        },
      }
    );
    expect(r1.status()).toBe(200);
    const action = await r1.json();
    expect(action.status).toBe("open");

    // Resolve
    const r2 = await request.post(
      `${BACKEND_URL}/api/action-center/actions/${action.id}/resolve`,
      {
        data: { resolution_note: "Résolu par E2E" },
      }
    );
    expect(r2.status()).toBe(200);
    const resolved = await r2.json();
    expect(resolved.status).toBe("resolved");
  });
});

import { expect, test } from "./fixtures/authenticated";

test.use({ storageState: "e2e/.auth/user.json" });

test.describe("Knowledge graph", () => {
  test("page loads and rebuild button is clickable", async ({ page }) => {
    await page.goto("/knowledge-graph");
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { level: 1, name: "Knowledge Graph" })).toBeVisible({
      timeout: 15000,
    });
    const rebuildButton = page.getByRole("button", { name: /Rebuild|Build Graph/i });
    await expect(rebuildButton).toBeVisible();
    await expect(rebuildButton).toBeEnabled();
  });
});

import { expect, test } from "./fixtures/authenticated";
import { attachTestPdf } from "./fixtures/upload";

test.use({ storageState: "e2e/.auth/user.json" });

test.describe("Upload", () => {
  test("can upload a PDF and see indexing status", async ({ page }) => {
    test.setTimeout(90_000);

    await page.goto("/chat");
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.getByPlaceholder("Message Omni AI...")).toBeVisible({ timeout: 15000 });

    await attachTestPdf(page);
  });
});

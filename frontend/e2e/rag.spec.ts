import { expect, test } from "./fixtures/authenticated";
import { attachTestPdf } from "./fixtures/upload";

test.use({ storageState: "e2e/.auth/user.json" });

test.describe("RAG", () => {
  test("uploaded document can be cited in chat response", async ({ page }) => {
    test.setTimeout(120_000);

    await page.goto("/chat");
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.getByPlaceholder("Message Omni AI...")).toBeVisible({ timeout: 15000 });

    await attachTestPdf(page);

    const input = page.getByPlaceholder("Message Omni AI...");
    await input.fill("What unique phrase appears in the uploaded Omni test document?");
    await input.press("Enter");

    await expect(page.getByText(/View retrieved chunks|Sources|test\.pdf|e2e verification/i).first()).toBeVisible({
      timeout: 90_000,
    });
  });
});

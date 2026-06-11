import path from "path";
import { expect, type Page } from "@playwright/test";

async function ensureBackendChatSession(page: Page) {
  const emptyState = page.getByRole("heading", { name: "How can I help you today?" });
  if (await emptyState.isVisible().catch(() => false)) {
    const input = page.getByPlaceholder("Message Omni AI...");
    await input.fill("E2E upload session");
    await input.press("Enter");
    await expect(page.getByRole("button", { name: "Stop generating" })).toBeHidden({ timeout: 60_000 });
  }
}

export async function attachTestPdf(page: Page, filename = "test.pdf") {
  await ensureBackendChatSession(page);

  const fixturePath = path.join(__dirname, "..", "fixtures", filename);
  const fileChooserPromise = page.waitForEvent("filechooser");
  await page.getByRole("button", { name: /Drop files or attach/i }).click();
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles(fixturePath);

  await expect(
    page
      .locator(`button[title="${filename}"]`)
      .or(page.getByText(/Uploading|Queued for indexing|Document ready|Upload failed/i))
      .first()
  ).toBeVisible({ timeout: 60_000 });

  await expect(page.getByText("Upload failed")).toHaveCount(0);
}

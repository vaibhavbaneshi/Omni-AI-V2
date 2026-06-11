import { expect, test } from "./fixtures/authenticated";

test.use({ storageState: "e2e/.auth/user.json" });

test.describe("Chat", () => {
  test("chat page loads successfully", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page.getByPlaceholder("Message Omni AI...")).toBeVisible({ timeout: 15000 });
  });

  test("can type a message and receive a response", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).not.toHaveURL(/\/login/);
    const input = page.getByPlaceholder("Message Omni AI...");
    await expect(input).toBeVisible({ timeout: 15000 });
    await input.fill("Say hello in one short sentence.");
    await input.press("Enter");

    await expect(page.locator(".group").filter({ has: page.locator("text=AI") }).first()).toBeVisible({
      timeout: 30000,
    });
  });

  test('can click "New Chat" and clear the message list', async ({ page }) => {
    test.setTimeout(90_000);

    await page.goto("/chat");
    await expect(page).not.toHaveURL(/\/login/);
    const input = page.getByPlaceholder("Message Omni AI...");
    await expect(input).toBeVisible({ timeout: 15000 });
    await input.fill("Quick test message");
    await input.press("Enter");
    await expect(page.getByRole("button", { name: "Stop generating" })).toBeHidden({ timeout: 60_000 });
    await page.getByRole("button", { name: "New chat" }).click();
    await expect(page.getByRole("heading", { name: "How can I help you today?" })).toBeVisible({
      timeout: 15000,
    });
  });
});

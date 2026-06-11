import { test, expect } from "@playwright/test";

test.describe("Auth", () => {
  test("login page loads at /login", async ({ page }) => {
    await page.goto("/login");
    await expect(page).toHaveURL(/\/login/);
  });

  test("Continue with Google button is visible", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("button", { name: /Continue with Google/i })).toBeVisible();
  });

  test("Continue with GitHub button is visible", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("button", { name: /Continue with GitHub/i })).toBeVisible();
  });

  test("navigating to /chat without auth redirects to /login", async ({ page }) => {
    await page.goto("/chat");
    await expect(page).toHaveURL(/\/login/);
  });
});

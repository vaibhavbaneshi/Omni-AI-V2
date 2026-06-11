import { test as base, expect } from "@playwright/test";
import fs from "fs";
import path from "path";

const AUTH_FILE = path.join(__dirname, "..", ".auth", "user.json");
const SESSION_KEY = "omni-ai-profile";

function readSessionValue(): string {
  const state = JSON.parse(fs.readFileSync(AUTH_FILE, "utf-8")) as {
    origins?: Array<{ sessionStorage?: Array<{ name: string; value: string }> }>;
  };
  const entry = state.origins?.[0]?.sessionStorage?.find((item) => item.name === SESSION_KEY);
  if (!entry?.value) {
    throw new Error(`Missing ${SESSION_KEY} in ${AUTH_FILE}. Run global setup via playwright test.`);
  }
  return entry.value;
}

export const test = base.extend({
  page: async ({ page }, use) => {
    const sessionValue = readSessionValue();
    await page.addInitScript(
      ({ key, value }) => {
        window.sessionStorage.setItem(key, value);
      },
      { key: SESSION_KEY, value: sessionValue }
    );
    await use(page);
  },
});

export { expect };

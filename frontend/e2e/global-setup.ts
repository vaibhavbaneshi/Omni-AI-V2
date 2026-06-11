import fs from "fs";
import path from "path";
import { config as loadEnv } from "dotenv";

async function globalSetup() {
  loadEnv({ path: path.join(__dirname, "..", ".env.test") });

  const backendUrl = process.env.TEST_BACKEND_URL || "http://localhost:8000";
  const baseUrl = process.env.TEST_BASE_URL || "http://localhost:3000";
  const authDir = path.join(__dirname, ".auth");
  const authFile = path.join(authDir, "user.json");

  fs.mkdirSync(authDir, { recursive: true });

  const response = await fetch(`${backendUrl}/auth/test-session`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Failed to create test session: ${response.status} ${await response.text()}`);
  }

  const payload = (await response.json()) as {
    access_token: string;
    refresh_token: string;
    email: string;
    username: string;
    name: string;
  };

  const cookies = response.headers.getSetCookie?.() ?? [];
  const parsedCookies = cookies.map((cookieLine) => {
    const [pair, ...attrs] = cookieLine.split(";").map((part) => part.trim());
    const [name, value] = pair.split("=");
    const cookie: Record<string, string | boolean | number> = {
      name,
      value,
      domain: "localhost",
      path: "/",
    };
    for (const attr of attrs) {
      const [key, val] = attr.split("=");
      const lower = key.toLowerCase();
      if (lower === "httponly") cookie.httpOnly = true;
      if (lower === "secure") cookie.secure = true;
      if (lower === "path" && val) cookie.path = val;
      if (lower === "domain" && val) cookie.domain = val.replace(/^\./, "");
    }
    return cookie;
  });

  const sessionValue = JSON.stringify({
    name: payload.name,
    email: payload.email,
    username: payload.username,
    createdAt: new Date().toISOString(),
    token: payload.access_token,
    refreshToken: payload.refresh_token,
  });

  const storageState = {
    cookies: parsedCookies,
    origins: [
      {
        origin: baseUrl,
        localStorage: [],
        sessionStorage: [{ name: "omni-ai-profile", value: sessionValue }],
      },
    ],
  };

  fs.writeFileSync(authFile, JSON.stringify(storageState, null, 2));
}

export default globalSetup;

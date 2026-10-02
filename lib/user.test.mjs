import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import test from "node:test";

const source = readFileSync(new URL("./user.ts", import.meta.url), "utf8");
const executableSource = source
  .replace(
    "export function getUserId(): string {",
    "function getUserId() {"
  )
  .replace("let newId: string;", "let newId;");

assert.notEqual(executableSource, source, "getUserId function was not found");

function callGetUserId(storage, cryptoApi) {
  return runInNewContext(`${executableSource}\ngetUserId()`, {
    window: { localStorage: storage },
    crypto: cryptoApi,
  });
}

test("returns an existing user ID without replacing it", () => {
  const storage = {
    getItem(key) {
      assert.equal(key, "study-ai-user-id");
      return "existing-user-id";
    },
    setItem() {
      assert.fail("existing ID should not be overwritten");
    },
  };

  assert.equal(callGetUserId(storage, {}), "existing-user-id");
});

test("uses crypto.randomUUID when available and stores the result", () => {
  let storedValue;
  const storage = {
    getItem: () => null,
    setItem(key, value) {
      assert.equal(key, "study-ai-user-id");
      storedValue = value;
    },
  };
  const cryptoApi = {
    randomUUID: () => "b2de6a92-e5e5-4eab-a542-80cf714fce5f",
    getRandomValues() {
      assert.fail("getRandomValues should not be used when randomUUID exists");
    },
  };

  const userId = callGetUserId(storage, cryptoApi);

  assert.equal(userId, "b2de6a92-e5e5-4eab-a542-80cf714fce5f");
  assert.equal(storedValue, userId);
});

test("generates a UUID v4 with getRandomValues when randomUUID is unavailable", () => {
  let storedValue;
  const storage = {
    getItem: () => null,
    setItem(key, value) {
      assert.equal(key, "study-ai-user-id");
      storedValue = value;
    },
  };
  const cryptoApi = {
    getRandomValues(bytes) {
      bytes.set(Array.from({ length: 16 }, (_, index) => index));
      return bytes;
    },
  };

  const userId = callGetUserId(storage, cryptoApi);

  assert.equal(userId, "00010203-0405-4607-8809-0a0b0c0d0e0f");
  assert.equal(storedValue, userId);
});

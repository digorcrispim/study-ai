import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import test from "node:test";

const source = readFileSync(new URL("./StudyQuiz.tsx", import.meta.url), "utf8");
const urlTemplate = source.match(
  /`http:\/\/127\.0\.0\.1:8000\/questions\/material\/\$\{materialId\}\/adaptive\/\$\{getUserId\(\)\}\$\{topicQuery\}[^`]*`/
)?.[0];

assert.ok(urlTemplate, "adaptive fetch URL template was not found");

test("adaptive request includes limit=5 with or without a topic", () => {
  const buildUrl = (topicQuery) =>
    runInNewContext(urlTemplate, {
      materialId: "material-1",
      getUserId: () => "user-1",
      topicQuery,
    });

  assert.equal(
    buildUrl(""),
    "http://127.0.0.1:8000/questions/material/material-1/adaptive/user-1?limit=5"
  );
  assert.equal(
    buildUrl("?topic=Costs%20and%20benefits"),
    "http://127.0.0.1:8000/questions/material/material-1/adaptive/user-1?topic=Costs%20and%20benefits&limit=5"
  );
});

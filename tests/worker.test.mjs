import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../cloudflare/worker.js", import.meta.url), "utf8");
const workerModule = await import(
  "data:text/javascript;base64," + Buffer.from(source, "utf8").toString("base64")
);
const worker = workerModule.default;

const expectedItems = [
  {
    profile_id: "tiktok_pieknemedia",
    theme: "humor",
    topic: "Humorystyczna obserwacja dnia",
    hook: "Mała rzecz, która zawsze wygląda inaczej w poniedziałek",
    format: "short",
    research_query: "nie dotyczy — treść autorska",
    editorial_note: "lekki, oryginalny humor"
  },
  {
    profile_id: "tiktok_ocenionona6",
    theme: "education",
    topic: "Jak działa pamięć robocza",
    hook: "Dlaczego czasem gubimy wątek?",
    format: "explainer",
    research_query: "pamięć robocza badania przegląd",
    editorial_note: "nie przedstawiać hipotez jako faktów"
  },
  {
    profile_id: "youtube_memoryagent",
    theme: "tech",
    topic: "Najnowsza zmiana w narzędziach AI",
    hook: "Co nowego w AI?",
    format: "short",
    research_query: "najnowsze wiadomości AI z ostatnich 24–72 godzin",
    editorial_note: "wymagane źródła przed produkcją"
  }
];

function createEnv(options = {}) {
  const statements = [];
  const state = { status: options.existingStatus ?? null };
  let aiCalls = 0;
  const DB = {
    prepare(sql) {
      const createBound = (params = []) => ({
        bind(...nextParams) {
          return createBound(nextParams);
        },
        async first() {
          if (sql.includes("SELECT status, started_at FROM daily_runs")) {
            return state.status ? { status: state.status, started_at: "2026-11-13 08:00:00" } : null;
          }
          if (sql.includes("SELECT COUNT(*) AS profile_count FROM profiles")) {
            return { profile_count: 3 };
          }
          return null;
        },
        async run() {
          statements.push({ sql, params });
          if (sql.includes("INSERT INTO daily_runs")) state.status = "running";
          if (sql.includes("UPDATE daily_runs SET status='succeeded'")) state.status = "succeeded";
          if (sql.includes("UPDATE daily_runs SET status='failed'")) state.status = "failed";
          return { success: true };
        },
        sql,
        params
      });
      return createBound();
    },
    async batch(batchStatements) {
      statements.push({
        batch: batchStatements.map(item => ({ sql: item.sql, params: item.params }))
      });
      return { success: true };
    }
  };
  const AI = {
    async run(model, args) {
      aiCalls += 1;
      assert.equal(model, "@cf/meta/llama-3.1-8b-instruct");
      assert.equal(args.response_format.type, "json_object");
      if (options.aiError) throw options.aiError;
      return { response: JSON.stringify(options.aiItems ?? { items: expectedItems }) };
    }
  };
  return {
    env: { DB, AI },
    statements,
    state,
    get aiCalls() { return aiCalls; }
  };
}

async function invokeScheduled(env, scheduledTime) {
  const pending = [];
  worker.scheduled(
    { scheduledTime, cron: "0 7,8 * * *" },
    env,
    { waitUntil(promise) { pending.push(promise); } }
  );
  await Promise.all(pending);
}

test("scheduled handler creates exactly three idempotent profile ideas at 09:00 Warsaw time", async () => {
  const fixture = createEnv();
  await invokeScheduled(fixture.env, Date.UTC(2026, 10, 13, 8));
  assert.equal(fixture.aiCalls, 1);
  assert.equal(fixture.state.status, "succeeded");
  const batch = fixture.statements.find(item => item.batch);
  assert.ok(batch);
  assert.equal(batch.batch.length, 6);
  assert.equal(batch.batch.filter(item => item.sql.includes("content_items")).length, 3);
  assert.equal(batch.batch.filter(item => item.sql.includes("daily_idea_created")).length, 3);
  const eventRows = batch.batch.filter(item => item.sql.includes("daily_idea_created"));
  const themes = eventRows.map(item => JSON.parse(item.params[3]).theme).sort();
  assert.deepEqual(themes, ["education", "humor", "tech"]);
});

test("scheduled handler skips the duplicate winter-time Cron invocation", async () => {
  const fixture = createEnv();
  await invokeScheduled(fixture.env, Date.UTC(2026, 10, 13, 7));
  assert.equal(fixture.aiCalls, 0);
  assert.equal(fixture.statements.length, 0);
});

test("scheduled handler does not regenerate a date already marked succeeded", async () => {
  const fixture = createEnv({ existingStatus: "succeeded" });
  await invokeScheduled(fixture.env, Date.UTC(2026, 10, 13, 8));
  assert.equal(fixture.aiCalls, 0);
  assert.equal(fixture.statements.length, 0);
});

test("invalid AI output marks the daily run failed and propagates the error", async () => {
  const fixture = createEnv({ aiItems: { items: [] } });
  await assert.rejects(
    invokeScheduled(fixture.env, Date.UTC(2026, 10, 13, 8)),
    /ai_output_wrong_item_count/
  );
  assert.equal(fixture.state.status, "failed");
});

test("health endpoint reports the D1 binding and all three profiles", async () => {
  const fixture = createEnv();
  const response = await worker.fetch(
    new Request("https://autored-idea-api.frozone-social.workers.dev/health"),
    fixture.env
  );
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.equal(body.status, "ok");
  assert.equal(body.profileCount, 3);
  assert.equal(body.timezone, "Europe/Warsaw");
});

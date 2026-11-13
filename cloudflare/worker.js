const TIME_ZONE = "Europe/Warsaw";
const MODEL_ID = "@cf/zai-org/glm-4.7-flash";
const TARGETS = [
  {
    id: "tiktok_pieknemedia",
    platform: "tiktok",
    handle: "@pieknemedia",
    editorial: "Humor sytuacyjny, codzienne życie, krótkie obserwacje i memiczny punkt zwrotny. Nie powielaj ostatnich tematów."
  },
  {
    id: "tiktok_ocenionona6",
    platform: "tiktok",
    handle: "@ocenionona6",
    editorial: "Treści merytoryczne: psychologia, nauka, technologia i mechanizmy codziennego świata. Nie przedstawiaj niezweryfikowanych twierdzeń jako faktów; przygotuj konkretne zapytanie badawcze."
  },
  {
    id: "youtube_memoryagent",
    platform: "youtube",
    handle: "@MemoryAgent-r3",
    editorial: "Kanał o najnowszej technologii i AI. Każdy temat musi przejść osobny research wiarygodnych źródeł z ostatnich 24–72 godzin; na tym etapie przygotuj wyłącznie propozycję tematu i zapytanie badawcze, bez udawania, że news został zweryfikowany."
  }
];

function localTimeParts(date) {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    hourCycle: "h23"
  }).formatToParts(date);
  return Object.fromEntries(parts.map((part) => [part.type, part.value]));
}

function extractJson(text) {
  const trimmed = String(text || "").trim();
  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start < 0 || end <= start) throw new Error("ai_output_not_json");
    return JSON.parse(trimmed.slice(start, end + 1));
  }
}

async function generateIdeas(env, localDate) {
  const prompt = [
    "Wygeneruj dokładnie trzy odrębne propozycje tematów — po jednej dla każdego profilu.",
    "Zwróć wyłącznie JSON: { \"items\": [{ \"profile_id\": string, \"topic\": string, \"hook\": string, \"format\": string, \"research_query\": string, \"editorial_note\": string }] }.",
    "Nie wymyślaj źródeł, dat, statystyk, cytatów ani faktów. Nie pisz, że research został wykonany.",
    "Nie twórz ani nie promuj treści o niebezpiecznych działaniach, środkach odurzających, hazardzie, broni, samookaleczeniu ani treści seksualnych.",
    "Dla YouTube Memory Agent zaproponuj temat do sprawdzenia w wiarygodnych źródłach z ostatnich 24–72 godzin; jeśli nie ma świeżego wydarzenia, zaproponuj research, nie news.",
    "Każdy profil musi dostać inny temat i inny format. Język polski.",
    "Data lokalna: " + localDate,
    "Profile: " + JSON.stringify(TARGETS)
  ].join("\n");

  const result = await env.AI.run(MODEL_ID, {
    messages: [
      { role: "system", content: "Jesteś redaktorem planującym treści. Nie konfabuluj. Zwracaj wyłącznie wymagany JSON." },
      { role: "user", content: prompt }
    ],
    max_tokens: 1800,
    response_format: { type: "json_object" },
    temperature: 0.65
  });

  const raw = result?.response ?? result?.choices?.[0]?.message?.content ?? result?.result?.choices?.[0]?.message?.content ?? result?.output_text ?? "";
  const parsed = extractJson(raw);
  if (!Array.isArray(parsed.items) || parsed.items.length !== 3) {
    throw new Error("ai_output_wrong_item_count");
  }

  const allowed = new Set(TARGETS.map((target) => target.id));
  const seen = new Set();
  for (const item of parsed.items) {
    if (!allowed.has(item.profile_id) || seen.has(item.profile_id)) {
      throw new Error("ai_output_invalid_profile_mapping");
    }
    seen.add(item.profile_id);
    for (const field of ["topic", "hook", "format", "research_query", "editorial_note"]) {
      if (typeof item[field] !== "string" || !item[field].trim()) {
        throw new Error("ai_output_missing_" + field);
      }
    }
  }
  if (seen.size !== 3) throw new Error("ai_output_missing_profile");
  return parsed.items;
}

async function runDaily(env, scheduledAt = new Date()) {
  const local = localTimeParts(scheduledAt);
  const localDate = local.year + "-" + local.month + "-" + local.day;
  if (local.hour !== "09") {
    return { status: "skipped", reason: "outside_local_schedule", localDate, localHour: local.hour };
  }

  const existing = await env.DB.prepare(
    "SELECT status, started_at FROM daily_runs WHERE local_date = ?"
  ).bind(localDate).first();

  if (existing?.status === "succeeded") {
    return { status: "skipped", reason: "already_processed", localDate };
  }
  if (existing?.status === "running") {
    const startedAt = Date.parse(String(existing.started_at || "").replace(" ", "T") + "Z");
    if (Number.isFinite(startedAt) && Date.now() - startedAt < 30 * 60 * 1000) {
      return { status: "skipped", reason: "run_still_active", localDate };
    }
  }

  await env.DB.prepare(
    "INSERT INTO daily_runs (local_date, status, started_at) VALUES (?, 'running', CURRENT_TIMESTAMP) " +
    "ON CONFLICT(local_date) DO UPDATE SET status='running', started_at=CURRENT_TIMESTAMP, completed_at=NULL, error_code=NULL " +
    "WHERE daily_runs.status IN ('failed','skipped','running')"
  ).bind(localDate).run();

  try {
    const ideas = await generateIdeas(env, localDate);
    const insert = env.DB.prepare(
      "INSERT OR IGNORE INTO content_items (id, profile_id, topic, title, description, hashtags_json, script, source_urls_json, rights_reference, status, daily_run_date) " +
      "VALUES (?, ?, ?, ?, '', '[]', '', '[]', '', 'idea', ?)"
    );
    const eventInsert = env.DB.prepare(
      "INSERT OR IGNORE INTO events (id, event_type, profile_id, content_id, detail_json) VALUES (?, 'daily_idea_created', ?, ?, ?)"
    );

    const statements = [];
    for (const item of ideas) {
      const id = "idea_" + localDate + "_" + item.profile_id;
      statements.push(insert.bind(id, item.profile_id, item.topic, item.hook, localDate));
      statements.push(eventInsert.bind(
        "event_idea_" + localDate + "_" + item.profile_id,
        item.profile_id,
        id,
        JSON.stringify({
          localDate,
          format: item.format,
          research_query: item.research_query,
          editorial_note: item.editorial_note,
          stage: "idea_only"
        })
      ));
    }
    await env.DB.batch(statements);
    await env.DB.prepare(
      "UPDATE daily_runs SET status='succeeded', completed_at=CURRENT_TIMESTAMP, result_count=? WHERE local_date=?"
    ).bind(ideas.length, localDate).run();

    return { status: "succeeded", localDate, resultCount: ideas.length };
  } catch (error) {
    await env.DB.prepare(
      "UPDATE daily_runs SET status='failed', completed_at=CURRENT_TIMESTAMP, error_code=? WHERE local_date=?"
    ).bind(error instanceof Error ? error.message.slice(0, 80) : "unknown_error", localDate).run();
    throw error;
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/health") {
      try {
        const row = await env.DB.prepare("SELECT COUNT(*) AS profile_count FROM profiles").first();
        return Response.json({
          service: "AUTORED IDEA",
          status: "ok",
          database: "connected",
          profileCount: row?.profile_count ?? 0,
          scheduledLocalTime: "09:00",
          timezone: TIME_ZONE
        });
      } catch {
        return Response.json({ service: "AUTORED IDEA", status: "degraded", database: "unavailable" }, { status: 503 });
      }
    }
    return Response.json({ error: "not_found" }, { status: 404 });
  },

  async scheduled(controller, env, ctx) {
    ctx.waitUntil(runDaily(env, new Date(controller.scheduledTime)));
  }
};

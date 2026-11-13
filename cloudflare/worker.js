const TIME_ZONE = "Europe/Warsaw";
const MODEL_ID = "@cf/meta/llama-3.1-8b-instruct";
const TARGETS = [
  {
    id: "tiktok_pieknemedia",
    platform: "tiktok",
    handle: "@pieknemedia",
    theme: "humor",
    editorial: "Humor sytuacyjny, codzienne życie, krótkie obserwacje i memiczny punkt zwrotny. Nie powielaj ostatnich tematów."
  },
  {
    id: "tiktok_ocenionona6",
    platform: "tiktok",
    handle: "@ocenionona6",
    theme: "education",
    editorial: "Treści merytoryczne: psychologia, nauka, technologia i mechanizmy codziennego świata. Nie przedstawiaj niezweryfikowanych twierdzeń jako faktów; przygotuj konkretne zapytanie badawcze."
  },
  {
    id: "youtube_memoryagent",
    platform: "youtube",
    handle: "@MemoryAgent-r3c",
    theme: "tech",
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
    "Zwróć wyłącznie JSON: { \"items\": [{ \"profile_id\": string, \"theme\": \"humor\"|\"education\"|\"tech\", \"topic\": string, \"hook\": string, \"format\": string, \"research_query\": string, \"editorial_note\": string }] }.",
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
    max_tokens: 1200,
    response_format: { type: "json_object" },
    temperature: 0.5
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
    const target = TARGETS.find((candidate) => candidate.id === item.profile_id);
    if (item.theme !== target.theme) throw new Error("ai_output_invalid_theme");
    for (const field of ["topic", "hook", "format", "research_query", "editorial_note"]) {
      if (typeof item[field] !== "string" || !item[field].trim()) {
        throw new Error("ai_output_missing_" + field);
      }
    }
  }
  if (seen.size !== 3) throw new Error("ai_output_missing_profile");
  return parsed.items;
}

function validateHumorDraft(draft) {
  const errors = [];
  if (typeof draft?.title !== "string" || !draft.title.trim() || draft.title.length > 80) errors.push("invalid_title");
  if (typeof draft?.description !== "string" || !draft.description.trim() || draft.description.length > 2200) errors.push("invalid_description");
  if (!Array.isArray(draft?.hashtags) || draft.hashtags.length < 3 || draft.hashtags.length > 8) {
    errors.push("invalid_hashtags");
  } else if (draft.hashtags.some((tag) => typeof tag !== "string" || !/^#[\p{L}\p{N}_]{2,}$/u.test(tag))) {
    errors.push("invalid_hashtag_format");
  }
  if (!Array.isArray(draft?.script) || draft.script.length < 3 || draft.script.length > 5) {
    errors.push("invalid_scene_count");
  } else if (draft.script.some((scene) =>
    typeof scene?.scene !== "string" || !scene.scene.trim() ||
    !Number.isFinite(scene.duration_seconds) || scene.duration_seconds < 2 || scene.duration_seconds > 15
  )) {
    errors.push("invalid_scene");
  }
  const duration = Number(draft?.duration_seconds);
  if (!Number.isFinite(duration) || duration < 20 || duration > 45) errors.push("invalid_duration");
  if (Array.isArray(draft?.script)) {
    const sceneDuration = draft.script.reduce((sum, scene) => sum + Number(scene?.duration_seconds || 0), 0);
    if (Math.abs(sceneDuration - duration) > 2) errors.push("scene_duration_mismatch");
  }
  if (typeof draft?.voiceover_text !== "string" || draft.voiceover_text.trim().length < 40) errors.push("invalid_voiceover");
  if (typeof draft?.visual_direction !== "string" || !draft.visual_direction.trim()) errors.push("missing_visual_direction");

  // Structural validation only. Every generated draft remains pending an independent safety review.
  return errors;
}

async function generateHumorDraft(env, idea, localDate) {
  const prompt = [
    "Napisz oryginalny, krótki scenariusz humorystyczny po polsku dla TikToka @pieknemedia.",
    "Temat i hook są inspiracją; nie kopiuj cudzych tekstów ani memów.",
    "Wyłącznie bezpieczny humor sytuacyjny z codziennego życia. Bez wyśmiewania konkretnych osób lub grup, bez stereotypów, obelg i treści seksualnych.",
    "Nie twórz treści o niebezpiecznych działaniach, ryzykownych wyzwaniach, używkach, hazardzie, broni ani samookaleczeniu.",
    "Zwróć wyłącznie JSON: { \"title\": string, \"description\": string, \"hashtags\": string[], \"script\": [{ \"scene\": string, \"duration_seconds\": number }], \"voiceover_text\": string, \"visual_direction\": string, \"duration_seconds\": number }.",
    "3–5 scen, 20–45 sekund łącznie, 3–8 hashtagów. Nie dodawaj instrukcji ryzykownych zachowań.",
    "Idea: " + JSON.stringify(idea),
    "Data lokalna: " + localDate
  ].join("\\n");
  const result = await env.AI.run(MODEL_ID, {
    messages: [
      { role: "system", content: "Jesteś scenarzystą krótkich, oryginalnych i bezpiecznych treści komediowych. Zwracasz wyłącznie JSON." },
      { role: "user", content: prompt }
    ],
    max_tokens: 1000,
    response_format: { type: "json_object" },
    temperature: 0.65
  });
  const raw = result?.response ?? result?.choices?.[0]?.message?.content ?? result?.result?.choices?.[0]?.message?.content ?? result?.output_text ?? "";
  const draft = extractJson(raw);
  const errors = validateHumorDraft(draft);
  if (errors.length) throw new Error(errors.join(",").slice(0, 80));
  return draft;
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
    // Recover only a stale lease, using a conditional update so concurrent Cron
    // deliveries cannot both take ownership of the same daily run.
    await env.DB.prepare(
      "UPDATE daily_runs SET status='failed', error_code='stale_run_recovered' " +
      "WHERE local_date=? AND status='running' AND started_at <= datetime('now','-30 minutes')"
    ).bind(localDate).run();
  }

  // Claim the date atomically. A second concurrent invocation sees status=running
  // and receives zero changed rows instead of starting a duplicate generation.
  const claim = await env.DB.prepare(
    "INSERT INTO daily_runs (local_date, status, started_at) VALUES (?, 'running', CURRENT_TIMESTAMP) " +
    "ON CONFLICT(local_date) DO UPDATE SET status='running', started_at=CURRENT_TIMESTAMP, completed_at=NULL, error_code=NULL " +
    "WHERE daily_runs.status IN ('failed','skipped')"
  ).bind(localDate).run();
  if (claim?.meta?.changes === 0) {
    return { status: "skipped", reason: "run_claimed_by_another_invocation", localDate };
  }

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
          theme: item.theme,
          format: item.format,
          research_query: item.research_query,
          editorial_note: item.editorial_note,
          stage: "idea_only"
        })
      ));
    }
    await env.DB.batch(statements);

    let humorDraftStatus = "not_generated";
    const humorIdea = ideas.find((item) => item.profile_id === "tiktok_pieknemedia");
    if (humorIdea) {
      try {
        const draft = await generateHumorDraft(env, humorIdea, localDate);
        const contentId = "idea_" + localDate + "_tiktok_pieknemedia";
        await env.DB.batch([
          env.DB.prepare(
            "UPDATE content_items SET title=?, description=?, hashtags_json=?, script=?, status='draft', safety_review_status='pending', updated_at=CURRENT_TIMESTAMP " +
            "WHERE id=? AND profile_id='tiktok_pieknemedia' AND status='idea'"
          ).bind(draft.title, draft.description, JSON.stringify(draft.hashtags), JSON.stringify({
            scenes: draft.script,
            voiceover_text: draft.voiceover_text,
            visual_direction: draft.visual_direction,
            duration_seconds: draft.duration_seconds
          }), contentId),
          env.DB.prepare(
            "INSERT OR IGNORE INTO events (id, event_type, profile_id, content_id, detail_json) VALUES (?, 'draft_generated', 'tiktok_pieknemedia', ?, ?)"
          ).bind(
            "event_draft_" + localDate + "_tiktok_pieknemedia",
            contentId,
            JSON.stringify({
              localDate,
              stage: "draft_created_pending_safety_review",
              sceneCount: draft.script.length,
              durationSeconds: draft.duration_seconds,
              safetyReview: "pending"
            })
          )
        ]);
        humorDraftStatus = "draft_created_pending_safety_review";
      } catch (draftError) {
        humorDraftStatus = "draft_generation_failed";
        try {
          await env.DB.prepare(
            "INSERT OR IGNORE INTO events (id, event_type, profile_id, content_id, detail_json) VALUES (?, 'draft_generation_failed', 'tiktok_pieknemedia', ?, ?)"
          ).bind(
            "event_draft_failed_" + localDate + "_tiktok_pieknemedia",
            "idea_" + localDate + "_tiktok_pieknemedia",
            JSON.stringify({ localDate, error: draftError instanceof Error ? draftError.message.slice(0, 80) : "unknown_error" })
          ).run();
        } catch {}
      }
    }

    await env.DB.prepare(
      "UPDATE daily_runs SET status='succeeded', completed_at=CURRENT_TIMESTAMP, result_count=? WHERE local_date=?"
    ).bind(ideas.length, localDate).run();

    return { status: "succeeded", localDate, resultCount: ideas.length, humorDraftStatus };
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
    if (request.method === "GET" && url.pathname === "/ideas") {
      const localDate = url.searchParams.get("date") || "";
      const parsedDate = new Date(localDate + "T00:00:00Z");
      if (!/^\d{4}-\d{2}-\d{2}$/.test(localDate) || Number.isNaN(parsedDate.valueOf()) || parsedDate.toISOString().slice(0, 10) !== localDate) {
        return Response.json({ error: "invalid_date" }, { status: 400, headers: { "Cache-Control": "no-store" } });
      }
      try {
        const result = await env.DB.prepare(
          "SELECT c.id, c.profile_id, c.topic, c.title, e.detail_json " +
          "FROM content_items c " +
          "JOIN daily_runs d ON d.local_date = c.daily_run_date " +
          "LEFT JOIN events e ON e.content_id = c.id AND e.event_type = 'daily_idea_created' " +
          "WHERE c.daily_run_date = ? AND c.status = 'idea' AND d.status = 'succeeded' " +
          "ORDER BY c.profile_id"
        ).bind(localDate).all();
        const rows = result?.results ?? [];
        if (!rows.length) {
          return Response.json({ status: "empty", date: localDate, items: [] }, { status: 404, headers: { "Cache-Control": "no-store" } });
        }
        const items = rows.map((row) => {
          let detail = {};
          try { detail = JSON.parse(row.detail_json || "{}"); } catch {}
          return {
            content_id: row.id,
            profile_id: row.profile_id,
            topic: row.topic,
            hook: row.title,
            theme: detail.theme || "",
            format: detail.format || "",
            research_query: detail.research_query || "",
            editorial_note: detail.editorial_note || ""
          };
        });
        return Response.json(
          { status: "ok", date: localDate, items },
          { headers: { "Cache-Control": "no-store" } }
        );
      } catch {
        return Response.json({ error: "database_unavailable" }, { status: 503, headers: { "Cache-Control": "no-store" } });
      }
    }
    return Response.json({ error: "not_found" }, { status: 404 });
  },

  async scheduled(controller, env, ctx) {
    ctx.waitUntil(runDaily(env, new Date(controller.scheduledTime)));
  }
};


export { validateHumorDraft, generateHumorDraft };

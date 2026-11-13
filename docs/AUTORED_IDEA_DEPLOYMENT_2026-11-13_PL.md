# AUTORED IDEA — zapis wdrożenia Cloudflare

**Data:** 2026-11-13  
**Status:** DEPLOYED — warstwa pomysłów i harmonogramu, nie produkcyjna publikacja

## Zasoby

| Zasób | Wartość | Potwierdzenie |
|---|---|---|
| Worker | `autored-idea-api` | Cloudflare API: upload/deployment success |
| Aktywna wersja | `14de2dea-9949-47b2-b5b9-eddd1382fafc` | deployment list: 100% traffic |
| D1 database | `autored_idea_db` | utworzona, EU jurisdiction, primary region EEUR |
| D1 database ID | `5162eab4-2364-4481-95c1-50fdc3070d3e` | Cloudflare API |
| AI binding | `AI` | Worker settings potwierdza binding type ai |
| D1 binding | `DB` | Worker settings potwierdza binding type d1 |
| workers.dev | enabled | Cloudflare API |
| Cron | `0 7,8 * * *` UTC | Cloudflare schedules API |
| Strefa lokalna | `Europe/Warsaw`, 09:00 | kontrola godziny w kodzie Workera |

## Zawartość i zachowanie

- D1 zawiera profile `@ocenionona6`, `@pieknemedia`, `@MemoryAgent-r3`.
- Potwierdzono tabele aplikacyjne: `profiles`, `content_items`, `daily_runs`, `events`, `publication_jobs`, `quota_ledger`.
- Potwierdzono kolumnę `daily_run_date` i unikalny indeks `idx_content_daily_profile`.
- Worker ma handlery `fetch` i `scheduled`.
- Worker używa modelu `@cf/meta/llama-3.1-8b-instruct` z `response_format=json_object`.
- Model API przeszedł test prostego wyjścia JSON; zużycie testowe wyniosło 7.3426 neuronów.
- Dzienny proces ma utworzyć po jednej propozycji tematu dla każdego z trzech profili i zapisać ją jako `idea`.
- Identyfikatory pomysłów i zdarzeń są deterministyczne; unikalny indeks blokuje duplikaty tego samego profilu w danym dniu.
- Dwa wywołania Cron są celowe: zimą 08:00 UTC odpowiada 09:00 w Polsce, latem 07:00 UTC odpowiada 09:00. Kod pomija pozostałe wywołanie.
- Publiczne publikowanie nie jest zaimplementowane.

## Wyniki kontroli

**Najnowszy deployment:** `1790469c-0976-42ce-b285-00d97555e48c`, wersja `14de2dea-9949-47b2-b5b9-eddd1382fafc`, 100% ruchu. Worker zawiera ograniczenia bezpieczeństwa treści, wymuszenie JSON i deterministyczne identyfikatory zadań.

| Kontrola | Status | Uwagi |
|---|---|---|
| Worker upload | PASS | Cloudflare przyjął moduł i aktywował deployment |
| Worker bindings | PASS | AI i D1 widoczne w ustawieniach |
| Cron schedule | PASS | schedule widoczny w API |
| workers.dev enabled | PASS | ustawienie potwierdzone |
| D1 profile rows | PASS | dokładnie trzy oczekiwane profile |
| D1 schema | PASS | tabele, kolumny, indeksy oraz safety_review_status sprawdzone przez SQL |
| Workers AI JSON smoke test | PASS | prosty JSON; nie jest to jeszcze pełny test trzech pomysłów |
| Workers AI image smoke test | PASS | FLUX 1 Schnell zwrócił obraz Base64, ok. 356 KB; brak integracji z rendererem |
| Worker HTTP /health | PASS | GitHub Actions curl do endpointu zwrócił 200 i status ok |
| Pierwszy Cron run | NOT RUN | zaplanowany na następne lokalne 09:00 |
| Trzy pomysły zapisane w D1 | NOT RUN | oczekuje na pierwszy przebieg Cron |
| Research i weryfikacja źródeł | NOT RUN | osobny etap |
| Render wideo / obrazu | NOT RUN | osobny etap |
| Publikacja TikTok/YouTube | BLOCKED | brak adapterów i poświadczeń w Workerze |

## Bezpieczeństwo i koszty

- Zasoby są skonfigurowane na Cloudflare Workers Free; nie przełączano konta na Workers Paid.
- D1 jest ograniczona do jurysdykcji EU.
- Nie utworzono KV ani R2; duże pliki mediów nie trafiają do D1.
- Workers AI Free ma limit 10 000 neuronów/dzień. Po przekroczeniu darmowego limitu na Free kolejne wywołania mają być blokowane, nie płatne.
- Worker nie ma sekretów platform publikacyjnych.
- Health endpoint nie zwraca danych treści ani sekretów. Test HTTP /health przechodzi w GitHub Actions.
- Logi mają włączone maskowanie zapytań? Nie ustawiono osobnej reguły redakcji; przed dodaniem tokenów trzeba skonfigurować maskowanie i przetestować brak sekretów w logach.

## Ograniczenia

Wdrożony komponent nie jest jeszcze systemem AUTORED IDEA w pełnym zakresie. Jest to backend harmonogramu i propozycji tematów. Nie generuje jeszcze kompletnych filmów, postów ani metadanych i nie publikuje ich na platformach.

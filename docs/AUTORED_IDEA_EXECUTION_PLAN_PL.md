# AUTORED IDEA — plan realizacji etapami

**Wersja:** 0.5  
**Data:** 2026-11-13

| Etap | Zakres | Wynik | Test bramkowy | Status |
|---|---|---|---|---|
| 0 | Inwentaryzacja kont, limitów, repozytoriów, usług | stan bazowy i ograniczenia | odczyt niezależny z każdego źródła | VERIFIED — audyt bazowy |
| 1 | Architektura, model danych, bezpieczeństwo, DR i plan testów | dokumentacja techniczna v0.2 | pliki zapisane i ponownie odczytane | DONE — projekt bazowy |
| 2 | Repozytorium, CI, Cloudflare Worker, D1 i AI binding | testowalny backend bazowy | CI green, Worker upload, bindings, D1 schema i HTTP health po wdrożeniu | VERIFIED — health PASS, atomowy Cron claim wdrożony |
| 3 | Kalendarz redakcyjny i osobne strategie profili | pomysły dla 3 kont | Cron, deduplikacja i rozdzielenie profili | PARTIAL — Cron i ochrona przed duplikatami gotowe; pierwszy przebieg 09:00 Europe/Warsaw oczekuje |
| 4 | Generator tekstu + research + fact-check | kompletne metadane | JSON, źródła i walidacja | PARTIAL — 9/9 RSS feedów PASS; pełny pipeline research, weryfikacja faktów i batch 3 profili do zbudowania |
| 5 | Generator mediów + FFmpeg + walidacja plików | poprawne pliki końcowe | FFprobe, hash, decode test | PARTIAL — Piper/FFmpeg 1080×1920 H.264/AAC PASS; 3 profile themes PASS; integracja z manifestem publikacji do spięcia |
| 6 | Warstwa limitów, kolejka, idempotencja | bezpieczne zadania publikacyjne | timeout, retry, quota tests, D1 job persistence | PARTIAL — core + Publora client + D1 publication_jobs idempotency; kolejka retry i reconciler wymagają wdrożenia |
| 7 | Adapter TikTok @pieknemedia | testowany adapter | autoryzacja, upload test, odczyt statusu | PARTIAL — Publora draft→upload→schedule pipeline + D1 job record testowane; wymaga PUBLORA_API_KEY, CLOUDFLARE_API_TOKEN i live E2E |
| 8 | Adapter TikTok @ocenionona6 | testowany adapter | autoryzacja, upload test, odczyt statusu | BLOCKED — brak połączenia tego konta w Publora i backendowego poświadczenia |
| 9 | Adapter YouTube @MemoryAgent-r3c | testowany adapter | OAuth, upload prywatny, odczyt statusu | BLOCKED — Metricool ID ≠ vidIQ ID; wymaga prawidłowego OAuth w Publora i E2E |
| 10 | Monitoring, alerty i automatyczne naprawy | operacyjny runbook | symulacje awarii | PARTIAL — health endpoint i test CI; alerting oraz self-healing do zbudowania |
| 11 | Backup, restore i DR | kopie i odtworzenie | Time Travel restore + encrypted export/restore | PARTIAL — D1 Time Travel restore verified; encrypted daily export workflow + offline verifier prepared, secrets and encrypted artifact restore test pending |
| 12 | Testy E2E, test regresji, uruchomienie produkcyjne | system PRODUCTION VERIFIED | pełna macierz testów | NOT RUN — brak publikacji E2E i testu end-to-end wszystkich 3 profili |

| 13 | Preflight dostawcy Publora | bezpieczny test 3 kont i tokenów | read-only connection checks, exact YouTube ID | READY TO RUN — wymaga sekretu PUBLORA_API_KEY i dwóch dodatkowych połączeń OAuth |

## Reguły przejścia

- Etap zależny nie rozpoczyna się od produkcyjnej publikacji przed przejściem testów poprzedniego.
- Dokumentację aktualizować w tym samym commicie co zmiana implementacji.
- Zmiana zewnętrznego API wymaga aktualizacji adaptera, testów kontraktowych i dokumentacji.
- Błędy terminalne nie są ponawiane automatycznie.
- W przypadku blokady wymagającej logowania/akceptacji użytkownika status pozostaje BLOCKED; nie obchodzić blokady.
- Nie uznawać wdrożenia Workera za potwierdzenie poprawnego przebiegu Cron; wymagany jest pierwszy udany zapis w D1.

## Priorytet kolejności

Najpierw potwierdzić pierwszy Cron run i jakość pomysłów. Następnie zbudować research/fact-check i spiąć renderer z manifestem. Integracje publikacyjne dopiero po preflight trzech kont, potwierdzeniu legalnego dostępu, rzeczywistych limitów i możliwości publikacji publicznej.

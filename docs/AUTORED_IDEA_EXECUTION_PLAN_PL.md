# AUTORED IDEA — plan realizacji etapami

**Wersja:** 0.6  
**Data:** 2026-11-13

| Etap | Zakres | Wynik | Test bramkowy | Status |
|---|---|---|---|---|
| 0 | Inwentaryzacja kont, limitów, repozytoriów, usług | stan bazowy i ograniczenia | odczyt niezależny z każdego źródła | VERIFIED — audyt bazowy |
| 1 | Architektura, model danych, bezpieczeństwo, DR i plan testów | dokumentacja techniczna v0.2 | pliki zapisane i ponownie odczytane | DONE — projekt bazowy |
| 2 | Repozytorium, CI, Cloudflare Worker, D1 i AI binding | testowalny backend bazowy | CI green, Worker upload, bindings, D1 schema i HTTP health po wdrożeniu | VERIFIED — health PASS, atomowy Cron claim wdrożony |
| 3 | Kalendarz redakcyjny i osobne strategie profili | pomysły dla 3 kont | Cron, deduplikacja i rozdzielenie profili | PARTIAL — Cron i ochrona przed duplikatami gotowe; pierwszy przebieg 09:00 Europe/Warsaw oczekuje |
| 4 | Generator tekstu + research + fact-check | kompletne metadane | JSON, źródła i walidacja | PARTIAL — 9/9 RSS feedów PASS; Worker generuje 3 idee i jeden szkic humoru, który pozostaje pending safety review; pełny pipeline research i fact-check do spięcia |
| 5 | Generator mediów + FFmpeg + walidacja plików | poprawne pliki końcowe | FFprobe, hash, decode test | PARTIAL — Piper/FFmpeg H.264/AAC PASS; dodano walidację 9:16 TikTok i profili YouTube; media artifact pipeline i manifest do spięcia |
| 6 | Warstwa limitów, kolejka, idempotencja | bezpieczne zadania publikacyjne | timeout, retry, quota tests, D1 job persistence | PARTIAL — D1 job states, idempotency, provider routing, quota gates, retry classification, due-job dispatcher, GitHub Actions schedule, age-encrypted artifact handoff i TikTok pending-status reconciliation; live E2E nadal do potwierdzenia |
| 7 | Adapter TikTok @pieknemedia | testowany adapter | OAuth, Direct Post, media verification, privacy audit | PARTIAL — natywny Direct Post adapter, AES-GCM token vault, due-job dispatcher, age-encrypted artifact handoff i media/audio gates; wymaga OAuth, app audit dla publicznych postów i testu E2E |
| 8 | Adapter TikTok @ocenionona6 | testowany adapter | OAuth, Direct Post, media verification, privacy audit | PARTIAL — ten sam adapter i dispatcher obsługują profile mapowane osobno; brak tokenu OAuth i zgody właściciela konta |
| 9 | Adapter YouTube @MemoryAgent-r3c | testowany adapter | OAuth, exact channel ID, resumable upload, publishAt | PARTIAL — natywny uploader z chunked resume, runner, exact channel ID gate, API audit gate i dispatcher; wymaga Google OAuth i oficjalnego zatwierdzenia publicznego uploadu |
| 10 | Monitoring, alerty i automatyczne naprawy | operacyjny runbook | symulacje awarii | PARTIAL — health endpoint, CI i bezpieczne stany błędów; alerting, due-job watchdog i self-healing do zbudowania |
| 11 | Backup, restore i DR | kopie i odtworzenie | Time Travel restore + encrypted export/restore | PARTIAL — D1 Time Travel restore verified; encrypted daily export workflow + offline verifier prepared, secrets and encrypted artifact restore test pending |
| 12 | Testy E2E, test regresji, uruchomienie produkcyjne | system PRODUCTION VERIFIED | pełna macierz testów | NOT RUN — brak publikacji E2E i testu end-to-end wszystkich 3 profili |

| 13 | Preflight dostawcy Publora | bezpieczny test kont i limitów | read-only connection/account-context/D1 checks | READY TO RUN — wymaga PUBLORA_API_KEY, CLOUDFLARE_API_TOKEN i połączeń OAuth; Publora Starter nie wystarcza na codzienną publikację 3 profili |
| 14 | Native OAuth setup and approval | legalny dostęp do API platform | exact account verification, token rotation, audit state | BLOCKED — właściciel musi skonfigurować TikTok/Google OAuth; publiczne Direct Post wymaga oficjalnego audytu aplikacji |

## Reguły przejścia

- Etap zależny nie rozpoczyna się od produkcyjnej publikacji przed przejściem testów poprzedniego.
- Dokumentację aktualizować w tym samym commicie co zmiana implementacji.
- Zmiana zewnętrznego API wymaga aktualizacji adaptera, testów kontraktowych i dokumentacji.
- Błędy terminalne nie są ponawiane automatycznie.
- W przypadku blokady wymagającej logowania/akceptacji użytkownika status pozostaje BLOCKED; nie obchodzić blokady.
- Nie uznawać wdrożenia Workera za potwierdzenie poprawnego przebiegu Cron; wymagany jest pierwszy udany zapis w D1.

## Priorytet kolejności

Najpierw potwierdzić pierwszy Cron run i jakość pomysłów. Następnie zbudować research/fact-check, niezależną akceptację bezpieczeństwa i media artifact pipeline. Integracje publikacyjne uruchamiać dopiero po legalnym OAuth, weryfikacji dokładnych kont, oficjalnym audycie platformy oraz testach E2E. Nie obchodzić wymagań wieku ani weryfikacji.

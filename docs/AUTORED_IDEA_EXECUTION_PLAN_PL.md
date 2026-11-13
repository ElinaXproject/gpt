# AUTORED IDEA — plan realizacji etapami

**Wersja:** 0.3  
**Data:** 2026-11-13

| Etap | Zakres | Wynik | Test bramkowy | Status |
|---|---|---|---|---|
| 0 | Inwentaryzacja kont, limitów, repozytoriów, usług | stan bazowy i ograniczenia | odczyt niezależny z każdego źródła | VERIFIED — audyt bazowy |
| 1 | Architektura, model danych, bezpieczeństwo, DR i plan testów | dokumentacja techniczna v0.2 | pliki zapisane i ponownie odczytane | DONE — projekt bazowy |
| 2 | Repozytorium, CI, Cloudflare Worker, D1 i AI binding | testowalny backend bazowy | CI green, Worker upload, bindings, D1 schema | VERIFIED — bez testu HTTP health |
| 3 | Kalendarz redakcyjny i osobne strategie profili | pomysły dla 3 kont | Cron, deduplikacja i rozdzielenie profili | PARTIAL — Cron skonfigurowany; pierwszy przebieg oczekuje |
| 4 | Generator tekstu + research + fact-check | kompletne metadane | JSON, źródła i walidacja | PARTIAL — test JSON modelu; pełny batch i research niezaliczone |
| 5 | Generator mediów + FFmpeg + walidacja plików | poprawne pliki końcowe | FFprobe, hash, decode test | NOT RUN |
| 6 | Warstwa limitów, kolejka, idempotencja | bezpieczne zadania publikacyjne | timeout, retry, quota tests | PARTIAL — idempotencja w core i schedulerze; brak trwałej kolejki produkcyjnej |
| 7 | Adapter TikTok @pieknemedia | testowany adapter | autoryzacja, upload test, odczyt statusu | BLOCKED — brak adaptera i poświadczeń |
| 8 | Adapter TikTok @ocenionona6 | testowany adapter | autoryzacja, upload test, odczyt statusu | BLOCKED — brak adaptera i poświadczeń |
| 9 | Adapter YouTube @MemoryAgent-r3 | testowany adapter | OAuth, upload prywatny, odczyt statusu | BLOCKED — potwierdzenie kanału i OAuth |
| 10 | Monitoring, alerty i automatyczne naprawy | operacyjny runbook | symulacje awarii | NOT RUN |
| 11 | Backup, restore i DR | kopie i odtworzenie | test restore | BLOCKED — brak wybranej infrastruktury backupu |
| 12 | Testy E2E, test regresji, uruchomienie produkcyjne | system PRODUCTION VERIFIED | pełna macierz testów | NOT RUN |

## Reguły przejścia

- Etap zależny nie rozpoczyna się od produkcyjnej publikacji przed przejściem testów poprzedniego.
- Dokumentację aktualizować w tym samym commicie co zmiana implementacji.
- Zmiana zewnętrznego API wymaga aktualizacji adaptera, testów kontraktowych i dokumentacji.
- Błędy terminalne nie są ponawiane automatycznie.
- W przypadku blokady wymagającej logowania/akceptacji użytkownika status pozostaje BLOCKED; nie obchodzić blokady.
- Nie uznawać wdrożenia Workera za potwierdzenie poprawnego przebiegu Cron; wymagany jest pierwszy udany zapis w D1.

## Priorytet kolejności

Najpierw potwierdzić pierwszy Cron run i jakość pomysłów. Następnie zbudować research/fact-check i renderowanie mediów. Integracje publikacyjne dopiero po potwierdzeniu legalnego dostępu, rzeczywistych limitów i możliwości publikacji publicznej.

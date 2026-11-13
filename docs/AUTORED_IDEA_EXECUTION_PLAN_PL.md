# AUTORED IDEA — plan realizacji etapami

**Wersja:** 0.2  
**Data:** 2026-11-13

| Etap | Zakres | Wynik | Test bramkowy | Status |
|---|---|---|---|---|
| 0 | Inwentaryzacja kont, limitów, repozytoriów, usług | stan bazowy i ograniczenia | odczyt niezależny z każdego źródła | VERIFIED — audyt bazowy |
| 1 | Architektura, model danych, bezpieczeństwo, DR i plan testów | komplet dokumentacji technicznej v0.1 | pliki zapisane i ponownie odczytane | DONE — projekt bazowy, wymaga zatwierdzenia przed produkcją |
| 2 | Repozytorium, CI, testy kontraktowe i skan sekretów | testowalny szkielet | GitHub Actions i testy jednostkowe | VERIFIED — test repo run 43456515985 SUCCESS; core jest szkieletem bez adapterów |
| 3 | Kalendarz redakcyjny i osobne strategie profili | plan treści dla 3 kont | test deduplikacji i rozdzielenia profili | NOT RUN |
| 4 | Generator tekstu + research + fact-check | kompletne metadane | test źródeł i walidacji | NOT RUN |
| 5 | Generator mediów + FFmpeg + walidacja plików | poprawne pliki końcowe | FFprobe, hash, decode test | NOT RUN |
| 6 | Warstwa limitów, kolejka, idempotencja | bezpieczne zadania publikacyjne | timeout, retry, quota tests | PARTIAL — deterministyczne primitives core zaimplementowane; brak kolejki trwałej i testu platformowego |
| 7 | Adapter TikTok @pieknemedia | testowany adapter | autoryzacja, upload test, odczyt statusu | BLOCKED — plan i uprawnienia |
| 8 | Adapter TikTok @ocenionona6 | testowany adapter | autoryzacja, upload test, odczyt statusu | BLOCKED — autoryzacja w docelowym orkiestratorze |
| 9 | Adapter YouTube @MemoryAgent-r3 | testowany adapter | OAuth, upload prywatny, odczyt statusu | BLOCKED — potwierdzenie kanału i OAuth |
| 10 | Monitoring, alerty i automatyczne naprawy | operacyjny runbook | symulacje awarii | NOT RUN |
| 11 | Backup, restore i DR | kopie i odtworzenie | test restore | BLOCKED — brak wybranej infrastruktury |
| 12 | Testy E2E, test regresji, uruchomienie produkcyjne | system PRODUCTION VERIFIED | pełna macierz testów | NOT RUN |

## Reguły przejścia

- Etap zależny nie rozpoczyna się od produkcyjnej publikacji przed przejściem testów poprzedniego.
- Dokumentację aktualizować w tym samym commicie co zmiana implementacji.
- Zmiana zewnętrznego API wymaga aktualizacji adaptera, testów kontraktowych i dokumentacji.
- Błędy terminalne nie są ponawiane automatycznie.
- W przypadku blokady wymagającej logowania/akceptacji użytkownika status pozostaje BLOCKED; nie obchodzić blokady.

## Priorytet kolejności

Najpierw niezależne, darmowe i możliwe do zweryfikowania moduły. Integracje publikacyjne dopiero po potwierdzeniu legalnego dostępu, rzeczywistych limitów i możliwości publikacji publicznej.

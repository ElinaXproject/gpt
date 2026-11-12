# System jakości i rozwoju asystenta

Wersja: 1.1
Data: 2026-11-12
Status: wdrażany

## Cel

Podnosić skuteczność pracy przez lepsze rozumowanie, samodzielne użycie narzędzi, testowanie, trwałą dokumentację i kreatywne rozwiązywanie problemów. Nie zakładać samomodyfikacji modelu ani trenowania jego wag. Usprawnienia dotyczą procesu pracy, narzędzi, repozytoriów, pamięci projektowej i kontroli jakości.

## Reguły nadrzędne

1. Zacznij od istniejącego kontekstu i źródeł prawdy; nie pytaj ponownie o dostępne dane.
2. Sprawdź aktualne narzędzia i ich rzeczywiste schematy przed wywołaniem.
3. Zanim zmienisz system, wykonaj odczyt stanu bazowego.
4. Zachowuj działające elementy. Preferuj małe, odwracalne zmiany.
5. Nie deklaruj sukcesu bez potwierdzenia narzędzia i niezależnej kontroli wyniku.
6. Oddzielaj fakty, hipotezy, rekomendacje i działania wykonane.
7. Przy błędzie szukaj przyczyny źródłowej; nie powtarzaj ślepo tej samej operacji.
8. Po naprawie uruchom test docelowy i test regresyjny.
9. Korzystaj z dokumentacji producenta i repozytoriów źródłowych; sprawdzaj datę, licencję, koszty, wymagania i ograniczenia.
10. Priorytet mają rozwiązania bezpłatne, bez karty i bez abonamentu. Koszty hostingu, API, transferu i limitów należy wykazać osobno.
11. Nie ujawniaj ani nie zapisuj sekretów, tokenów, haseł i danych wrażliwych w logach lub repozytorium.
12. Nie wykonuj działań zewnętrznych o istotnych skutkach bez wymaganej zgody użytkownika.

## Cykl realizacji

1. Rozpoznanie: cel, kryteria akceptacji, kontekst, ograniczenia.
2. Research: dokumentacja oficjalna, repozytoria, issue/PR, porównanie licencji i kosztów.
3. Projekt: warianty, ryzyka, plan minimalnej zmiany i plan wycofania.
4. Wykonanie: małe kroki, kopia/branch, brak naruszania działającego systemu.
5. Test: test jednostkowy/integracyjny lub ręczny test ścieżki użytkownika.
6. Regresja: sprawdzenie krytycznych wcześniejszych funkcji.
7. Weryfikacja: ponowny odczyt rezultatu ze źródła docelowego.
8. Dokumentacja: decyzja, zmiany, wyniki testów, problemy otwarte i następny krok.

## Poziomy dowodu

- PLAN: pomysł lub plan, brak wykonania.
- DONE: narzędzie potwierdziło wykonanie, ale brak niezależnego testu.
- VERIFIED: rezultat odczytano ponownie i test przeszedł.
- BLOCKED: brak wymaganych uprawnień, danych, narzędzia lub zgody; wskazać konkretny powód.

## Testy jakości odpowiedzi i działania

Każdy test ma wejście, oczekiwany rezultat i kryterium zaliczenia. Zestaw regresyjny powinien obejmować:
- zgodność z poleceniem i kontekstem wcześniejszych ustaleń;
- poprawne rozpoznanie, kiedy potrzebny jest research;
- dobór właściwego narzędzia i argumentów;
- brak zmyślonych wyników, linków, terminów i statusów;
- zachowanie ograniczeń budżetowych i prywatności;
- sprawdzenie zapisu, publikacji lub wdrożenia;
- poprawne wznowienie pracy z dokumentacji;
- wykrywanie i raportowanie niepewności.

Nie oceniaj jakości wyłącznie przez model-as-judge. Łącz asercje deterministyczne, testy narzędzi, testy regresyjne i kontrolę człowieka tam, gdzie rezultat ma realne skutki.

## Wdrożenia w repozytorium — 2026-11-12

- Dodano `tests/test_workbench.py`: osiem deterministycznych testów sprawdzających wymagane dokumenty, kompletność przypadków E01–E10, statusy procesu, linki wewnętrzne, szablony i typowe formaty wycieków sekretów.
- Dodano `.github/workflows/quality.yml`: testy uruchamiają się przy push do main, pull request i ręcznie. Uprawnienia workflow ograniczono do `contents: read`. Akcje przypięto do pełnych SHA.
- Dodano `.github/dependabot.yml`: cotygodniowe aktualizacje GitHub Actions, limit pięciu otwartych PR.
- Pierwszy pełny przebieg GitHub Actions zakończył się statusem SUCCESS. Job „Documentation and safety regression tests” zakończony sukcesem; wszystkie kroki wykonane. Drugi zestaw obejmuje też kontrolę uprawnień CI, przypięcia SHA i konfiguracji Dependabot.
- To są testy repozytorium i dokumentacji, a nie dowód, że model stał się inteligentniejszy ani że integracje zewnętrzne działają.

## Proponowany darmowy stos open source

Wdrażać etapami, nie instalować wszystkiego naraz:
- Promptfoo (MIT): lokalne testy promptów, regresja i red-teaming; uruchomić dopiero po przygotowaniu neutralnych, niepoufnych przypadków testowych i sprawdzeniu kosztów modelu.
- Inspect AI (MIT): ewaluacje agentów w kontrolowanym środowisku.
- Langfuse (MIT core): śledzenie przebiegów i analiza jakości, jeśli pojawi się potrzeba oraz możliwość bezpiecznego self-hostingu.
- Cognee: kandydat do lokalnej pamięci długoterminowej; nie wdrażać, dopóki nie wykaże przewagi nad istniejącym Notion + Library.
- GitHub Actions: aktywna automatyzacja testów i aktualizacji zależności.

Przed wdrożeniem sprawdź aktualną licencję, aktywność projektu, wymagania sprzętowe, telemetrię, bezpieczeństwo i realne koszty. Nie instaluj usług na komputerze użytkownika bez jego zgody.

## Rejestr zmian

| Data | Zmiana | Dowód |
| --- | --- | --- |
| 2026-11-12 | Utworzono system jakości i rozwoju | Dokument w repozytorium i Notion |
| 2026-11-12 | Dodano testy deterministyczne i CI | GitHub Actions run 43247202462: SUCCESS (8 testów) |
| 2026-11-12 | Dodano cotygodniowy Dependabot dla GitHub Actions | `.github/dependabot.yml` zapisany; uruchomienie Dependabot zakończone SUCCESS |

## Otwarte prace

- [ ] Zbudować testy zachowania asystenta na rzeczywistych scenariuszach (pamięć, dobór narzędzi, prawdziwe potwierdzanie działań); nie mylić ich z testami plików.
- [ ] Dodać kontrolę bezpieczeństwa zależności i skanowanie sekretów bez wysyłania danych poufnych do zewnętrznych usług.
- [ ] Sprawdzić ustawienia ochrony gałęzi i wymagania PR; nie zmieniać ich bez potwierdzenia dostępności i skutków.
- [ ] Uporządkować status integracji Publora/n8n osobno od systemu jakości asystenta.
- [ ] Rozwiązać i zweryfikować upload do Dropbox; nie deklarować synchronizacji przed testem.
- [ ] Ocenić Promptfoo/Inspect AI na małym zestawie neutralnych testów, bez kupowania API.
- [ ] Nie wdrażać kolejnej bazy pamięci bez dowodu, że poprawi wyszukiwanie i ciągłość pracy.

# AUTORED IDEA — dziennik audytu i napraw

**Data:** 2026-11-14 (audyt danych z 2026-11-13)  
**Zakres:** repozytorium `ElinaXproject/gpt`, Publora, Metricool, Cloudflare Worker, GitHub Actions.  
**Zasada:** nie wykonywano nowych publikacji ani nie zmieniano połączeń kont.

## 1. Potwierdzone błędy publikacji TikTok

Historia Publora zawierała:
- 1 nieudaną próbę z PNG: `file_format_check_failed` — TikTok odrzucił format zdjęcia.
- 2 nieudane próby z JPEG: `picture_size_check_failed` — TikTok odrzucił rozmiar obrazu.
- Wszystkie trzy próby zakończyły się statusem terminalnym; nie były oznaczone jako bezpieczne do ponowienia bez zmiany pliku.
- Później jedna publikacja z tym samym tekstem została opublikowana poprawnie.
- Druga opublikowana pozycja w historii miała inną treść (mem z kotem), więc nie jest duplikatem pierwszej.
- Znaleziono też dwa puste szkice bez treści, platform i mediów.

Nie wolno ponawiać niezmienionego pliku po błędach formatu lub rozmiaru. Najpierw trzeba go poprawić i zweryfikować.

## 2. Wdrożona poprawka

Commit `15b17049dad0d681322e70daaa9de555b93121d3`:
- dodano normalizację zdjęć TikTok przed uploadem;
- obrazy są obracane zgodnie z EXIF, zmniejszane do maksymalnie 1080 × 1080 z zachowaniem proporcji i kodowane jako JPEG;
- przezroczystość jest składana na białym tle;
- oryginalny plik nie jest modyfikowany;
- plik tymczasowy jest usuwany po uploadzie.

Commit `b6dff73a60c358afce6e6c9dbcf1a0cebd8b0d08`:
- dodano zależność Pillow potrzebną do bezpiecznej normalizacji.

Commit `0e1d0f546cfa5eff598596ba095f2afe2c7d1984`:
- dodano test dużego PNG 2400 × 1800;
- test sprawdza, że upload otrzymuje JPEG o maksymalnym wymiarze 1080 px, a plik źródłowy pozostaje bez zmian.

Commit `5ee68a5b100bdfd8f449fc0069c8fb600f533dc6`:
- przeniesiono normalizację przed utworzenie szkicu dostawcy, aby wadliwy obraz nie pozostawiał pustego szkicu.

## 3. Wynik testów po poprawce

GitHub Actions run: `43528286480`  
Commit: `5ee68a5b100bdfd8f449fc0069c8fb600f533dc6`  
Wynik: **SUCCESS**.

Zaliczone kroki:
- pełne testy regresyjne Python;
- kontrola składni Cloudflare Worker;
- testy harmonogramu i health Workera;
- health wdrożonego Workera;
- walidacja read-only endpointu ideas.

To potwierdza poprawność testów i wdrożonego Workera, ale nie jest testem publikacji na żywym koncie.

## 4. Blokady integracji wykryte podczas audytu

### Publora
- aktywne połączenie: TikTok `@pieknemedia`;
- plan Starter: 13 z 15 publikacji pozostało w bieżącym okresie;
- 3 wolne sloty kolejki;
- brak połączenia Publora dla `@ocenionona6` i kanału YouTube.

### Metricool
- istnieje brand `RED ABSURD IDEA`;
- TikTok: `ocenionona6`;
- YouTube ID zwracany przez Metricool: `UCRmmEQysOmUbs8mpZEOgtLw`;
- nie potwierdzono, że ten identyfikator odpowiada kanałowi `@MemoryAgent-r3c`;
- skrypt preflight w repozytorium oczekuje innego YouTube ID (`UCOE1EX9WZGDesaJNYIEhj7g`), więc kontrola tożsamości kanału blokuje gotowość.

### Orkiestracja
- obecny Cloudflare Worker generuje propozycje tematów i udostępnia endpointy kontrolne;
- workflow GitHub Actions sprawdza jakość kodu i health, ale nie jest harmonogramem produkcyjnych publikacji;
- nie potwierdzono automatycznego, end-to-end przepływu od researchu i renderowania do publikacji dla wszystkich trzech profili;
- nie wolno oznaczać systemu jako produkcyjnie gotowego, dopóki nie zostanie potwierdzony adapter, autoryzacja, limit, status publikacji i deduplikacja dla każdego konta.

## 5. Następne prace

1. Rozdzielić adaptery: Publora dla `@pieknemedia`, Metricool dla `@ocenionona6`, oraz potwierdzić właściwy kanał YouTube przed przypisaniem.
2. Dodać kontrolę duplikatów na poziomie treści i profilu, nie tylko identyfikatora zadania.
3. Dodać walidację pustych szkiców i ich bezpieczne czyszczenie po potwierdzeniu, że nie zawierają pracy użytkownika.
4. Zbudować i przetestować harmonogram produkcyjny, retry z backoff, dead-letter queue, monitoring oraz odzyskiwanie.
5. Przeprowadzić kontrolowany test publikacji dla każdego konta, z weryfikacją końcowego statusu i bez powielania postów.


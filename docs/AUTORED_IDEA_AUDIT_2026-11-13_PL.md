# AUTORED IDEA — audyt stanu początkowego

**Data i czas:** 2026-11-13, ok. 16:45 Europe/Warsaw  
**Repo:** `ElinaXproject/gpt`, gałąź `main`  
**Status:** odczyty potwierdzone; nie wykonano publikacji ani nie zmieniono kont.

## 1. Potwierdzone odczyty

| System | Wynik odczytu | Wniosek |
|---|---|---|
| GitHub | Repozytorium istnieje, widoczność publiczna, uprawnienia admin/push aktywne | można wersjonować dokumentację i kod |
| Activepieces | Projekt `Memory's Project`; 0 flow, 0 connections | wcześniejszy workflow nie istnieje już w tym projekcie; tabele pozostały |
| Activepieces tables | 4 tabele: Integracje i konfiguracja (4 rekordy), Dziennik automatyzacji (8), Biblioteka mediów (2), Kalendarz treści (10) | można wykorzystać jako punkt startowy po audycie schematu i retencji |
| Publora | Starter, limit 15 postów/mies., 2 użyte, 13 pozostało; 3 sloty harmonogramu, 7 dni; 1/3 połączeń | nie pokrywa wysokiej częstotliwości publikacji |
| Publora connection | TikTok `@pieknemedia`, status active, token valid, brak lastError, ostatni udany post 2026-11-12 | kanał połączony |
| Metricool | Marka `RED ABSURD IDEA`, Europe/Warsaw; sieć TikTok `ocenionona6`, YouTube channel ID `UCRmmEQysOmUbs8mpZEOgtLw` | istnieje podłączenie TikTok @ocenionona6 i kanał YouTube w tej marce |
| Activepieces auth | 0 połączeń OAuth/API | brak bezpośredniego połączenia Publora/Metricool/Google w orkiestratorze |

## 2. Ważne rozbieżności i ryzyka

- W poprzedniej dokumentacji operacyjnej Activepieces opisano aktywny flow 12 kroków. Bieżący odczyt zwrócił 0 flow. Aktualny stan narzędzia ma pierwszeństwo; nie deklarować, że flow działa.
- Tabele Activepieces zawierają stare wpisy i tymczasowe URL-e plików. Nie używać ich do publikacji bez ponownego sprawdzenia ważności URL, MIME, rozmiaru i praw.
- Wpisy w kalendarzu mają status `Do przygotowania` / `Wstrzymane`; nie ma dowodu, że zostały opublikowane.
- Poprzedni dziennik opisuje błędy Publora: nieobsługiwane rozmiary JPEG i PNG. Walidacja mediów musi uwzględniać rzeczywiste wymagania każdego adaptera.
- Plan Publora Starter ma limit 15 publikacji miesięcznie. Historyczna konfiguracja Metricool Free wskazywała 20 publikacji miesięcznie, ale bieżący odczyt nie zweryfikował aktualnego zużycia i limitu Metricool — traktować jako niepotwierdzone do ponownego odczytu.
- YouTube ID w Metricool jest widoczny, ale nie potwierdzono, że należy do uchwytu `@MemoryAgent-r3`. Wymagany test kanału.
- Brak autoryzacji TikTok Content Posting API i Google OAuth w Activepieces.

## 3. Decyzje bazowe

1. Nie odtwarzać starego flow FROZONE bez audytu i nowego projektu.
2. Zachować istniejące tabele, ale nie traktować starych danych jako aktywnych zleceń.
3. Nie uruchamiać publikacji automatycznej ani nie wysyłać publicznych postów w trakcie testów.
4. Nie używać nieoficjalnych API, nie omijać limitów, nie tworzyć wielu projektów API w celu obejścia limitów.
5. Nie wdrażać Cloudflare R2 ani płatnego magazynu.
6. GitHub pozostaje źródłem wersjonowanej dokumentacji i kodu.
7. Każdy kanał musi przejść oddzielny test mapowania konta.

## 4. Wymagane dalsze potwierdzenia

- TikTok Developer App: właściciel, status audytu, scope `video.publish`, autoryzacje obu kont.
- Metricool: aktualny plan, limit i wykorzystanie, możliwość obsługi YouTube i TikTok dla wskazanych profili.
- Publora: dokładny zakres limitu, harmonogram i autoAddMusic dla zdjęć.
- YouTube: identyfikacja kanału po uchwycie, OAuth `youtube.upload`, status projektu API.
- Hosting: gdzie ma działać scheduler/worker 24/7 bez kosztu i bez karty.
- Backup: darmowe, szyfrowane i odseparowane miejsce oraz realny test restore.

## 5. Weryfikacja

Odczyty wykonano przez połączone integracje GitHub, Activepieces, Publora i Metricool. Nie ujawniono sekretów ani tokenów. Żadna publikacja nie została utworzona.

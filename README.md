# POV+ pro Kodi · 0.1.2 (experimentální)

Samostatný fork POV 6.10.23 pro osobní použití. ID `plugin.video.povplus`, vlastní profil, cache, okna a nastavení. Lze instalovat vedle původního POV. Projekt je oddělený od domácího panelu, FilmWatch i Cometu na Orange Pi.

## Nastavení TMDb

Pro filmový katalog je nutný vlastní **API Read Access Token**, který získáš v [TMDb → Settings → API](https://www.themoviedb.org/settings/api) a vložíš v POV+ → Nastavení → Metadata. Jde o jiný údaj než API Key. **My Services → TMDbList** je volitelné párování osobních seznamů; předpokládá již vyplněný Read Access Token. Od 0.1.2 se chybějící token nebo odmítnuté párování hlásí uživateli.

## Oprava 0.1.1

Verze 0.1.0 chybně směrovala odkazy do původního POV. Aktualizuj na 0.1.1 a restartuj Kodi. Není nutná nová instalace repozitáře ani mazání účtů.

## Co tato verze přidává

- Přísný filtr ve výsledcích vyhledávání, automatickém přehrávání i náhradní větvi „ignorovat filtry“: vyloučí rozpoznané CAM/TS/TC/SCR a zdroje pod nastavenou kvalitou nebo nad datovým limitem. Vypnutí přísného filtru je výslovná volba v nastavení.
- Výchozí minimum 1080p a průměrný limit 40 Mbit/s pro připojení 50 Mbit/s. Neznámá velikost nebo délka filmu se v přísném režimu nepřijímá. Velikosti interního POV se interpretují jako GiB. Jde o odhad z údajů poskytovatele; ne o měření špiček, obrazu či kompatibility TV.
- `POV+ · Český výběr, hodnocení a kvalita` v hlavním menu. Filtry ČSFD alespoň 0–100 %, jeden nebo více žánrů (OR), minimum 720p/1080p/4K a nalezená kvalita v limitu.
- Přepnutí zdroje přehledu: digitální / disková vydání za posledních 31 dnů, TMDb trendy týdne, Trakt nejsledovanější týdne a TMDb populární filmy. Digitální vydání používají světový/US katalog, nikoli potvrzení nabídky v ČR. Kino premiéry nejsou zdrojem této nabídky. Vydání v katalogu není důkazem ripu na RD; zdroje se vyhledávají samostatně.
- Hvězdičky + přesná procenta ČSFD u názvů filmů, nativní pojmenované hodnocení `csfd`, detail, ruční propojení ČSFD a dostupné komentáře/recenze s uvedením původu. Není potřeba speciální skin.
- Detail nabízí původní přehrávání a správu Trakt. Účty z původního POV se automaticky nekopírují. Autorizují se samostatně v POV+.

## Důležitý stav ČSFD

**Přímé načtení ČSFD z tohoto pracovního prostředí dne 30. 10. 2026 skončilo ochranou proti automatickému čtení. Živé hodnocení ani recenze se proto nepodařilo ověřit.** Parser a párování jsou otestované na syntetických datech. Struktura polí hodnocení, roku a uživatelských recenzí byla ověřena proti [ČSFD.cz scraperu 3.49 od SikySikov](https://github.com/sikysikov/sikyaddons/tree/master/repo/metadata.csfd.cz) (GPL v3). Jeho `metadata.csfdcz.helper` doplňuje TMDb metadata; neposkytuje API pro ČSFD a není pro POV+ vyžadován. Instalace knihovního scraperu sama nepřepne metadata seznamů POV+. Doplněk ochranu neřeší ani neobchází; při blokaci zobrazí `ČSFD —`. Takový film neprojde filtrem např. 70 %.

Automatické propojení vyžaduje jedinou shodu názvu a roku. Pokud profil obsahuje IMDb ID, musí se shodovat. Nejednoznačná shoda se nikdy nevybírá podle prvního výsledku. V detailu lze vložit konkrétní ČSFD URL/ID a potvrdit správný film.

Volitelně lze v nastavení připojit vlastní **node-csfd-api** server (dokumentované cesty `/search/:query`, `/movie/:id`). To nezaručuje přístup, pokud ČSFD odmítá i tento server. ČSFD komentáře se zobrazí pouze pokud jsou obsažené v dostupné stránce; jinak detail zkusí české recenze TMDb a uvede jejich původ. Nedostupné recenze se nevyrábějí a rating se nenahrazuje IMDb/TMDb procenty.

## Instalace ze ZIPu nebo Kodi repozitáře

1. Stáhni [instalátor Kodi repozitáře](https://raw.githubusercontent.com/kudykam/pov-plus/main/docs/repository.kudykam.povplus/repository.kudykam.povplus-0.1.0.zip), nainstaluj jej v Kodi přes **Instalovat ze ZIP souboru** a poté zvol **Instalovat z repozitáře → POV+ Repository → Doplňky videa → POV+**. Pro přímou instalaci lze stáhnout [ZIP doplňku](https://raw.githubusercontent.com/kudykam/pov-plus/main/docs/plugin.video.povplus/plugin.video.povplus-0.1.2.zip). Pokud máš distribuční balík, rozbal jej; v `dist/` je `plugin.video.povplus-0.1.2.zip` a `repository.kudykam.povplus-0.1.0.zip`.
2. Přenes instalační ZIP do místa dostupného Kodi. V Kodi otevři **Doplňky → Instalovat ze ZIP souboru** a vyber `plugin.video.povplus-0.1.2.zip`. Pokud Kodi žádá povolení neznámých zdrojů, povoluješ tím instalaci vlastních doplňků.
3. V nastavení **Metadata** vlož vlastní **TMDb API Read Access Token**. Pro Trakt nastav vlastní **Client ID a Client Secret** registrované aplikace. Původní výchozí TMDb bearer token ani Trakt client secret z upstreamu tento fork nepublikuje. Párování zobrazí kód a adresu poskytovatele; autorizační kódy se neposílají externím QR službám ani zkracovačům URL. Real-Debrid používá původní veřejný device flow.
4. Spusť **POV+**. V jeho nastavení → Accounts / My Services znovu autorizuj Real-Debrid a Trakt. Nepřenášej ani nesdílej `settings.xml` s účtovými tokeny.
5. Nové volby jsou v poslední kategorii **POV+ · Český výběr**. Začni bez filtru hodnocení (0 %), ověř ČSFD u několika filmů a teprve potom nastav např. 70 %.
6. Otevři novou položku POV+ v hlavním menu. Kontrola první stránky může trvat několik minut; lze ji zrušit mezi filmy. Kladný výsledek se ukládá hodinu, kontrola bez vyhovujícího zdroje 15 minut. Filtr platí pro aktuální stránku kandidátů, další stránka zůstává dostupná i při prázdném výsledku.

Při vypnuté TV doplněk neběží a nic nevyhledává. Tato varianta sama nevyžaduje Orange Pi.

## Vlastní GitHub repozitář a aktualizace

Veřejný repozitář: [kudykam/pov-plus](https://github.com/kudykam/pov-plus), větev `main`.

- Zdroj doplňku: `plugin.video.povplus/`.
- Instalační repozitář: `repository.kudykam.povplus/`.
- Statická distribuce: `docs/` včetně ZIPů, `addons.xml`, kontrolního MD5 pro Kodi a SHA-256 balíků.
- Kodi repozitář používá veřejné raw GitHub URL. Po prvním nainstalování repozitářového ZIPu umí Kodi aktualizace stahovat bez GitHub Pages.
- Pro pohodlné přidání HTTP zdroje přímo v Kodi lze po nahrání povolit **Settings → Pages → Deploy from a branch → main /docs**. Dokud Pages nejsou povolené a nasazené, není webová adresa zdroje funkční.
- Při změně vlastníka/názvu/větve přestav balíky: `python tools/build_repo.py --owner JMENO --repository pov-plus --ref main`.
- Při další verzi změň číslo v `plugin.video.povplus/addon.xml`, spusť testy a sestavení a commitni také nové soubory v `docs/`. Původní POV aktualizace tento doplněk nepřepisují; opravy z upstreamu se přebírají ručně.

## Ověření

`python -m unittest discover -s tests -v`

`python -m compileall -q plugin.video.povplus`

`python tools/build_repo.py`

Automatické testy pokrývají hranice filtru, obejití původních filtrů, bitrate v GiB, neznámá data, shodu ČSFD, ochrannou stránku, cache a menu s náhradou Kodi API. **Skutečný Kodi runtime, instalace v TV, účty, dekódování a živé ČSFD nejsou otestované. Tato první verze je určena k ověření vedle původního doplňku.**

## Původ a licence

Vychází z instalačního zdroje [POV 6.10.23](https://kodifitzwell.github.io/repo/plugin.video.pov/plugin.video.pov-6.10.23.zip), který v `addon.xml` uvádí GNU GPL v3. Původní autorské poznámky a zdrojové soubory zůstávají zachované; upravené soubory jsou označené datem. Tento fork není oficiální POV a není propojený s Kodi, Real-Debrid, Trakt ani ČSFD. Licence a odpovídající zdroj jsou součástí balíku. Viz `LICENSE`, `UPSTREAM.json`, `CHANGES.md`.

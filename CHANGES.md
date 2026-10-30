# Změny POV+ · 30. 10. 2026

- Změna ID doplňku, profilových cest a URL na plugin.video.povplus.
- Oddělení interního provider balíčku na lib/povplus, oknových property prefixů a dat.
- Přísná politika kvality, zákazu prerelease a průměrného toku ve finální hranici zobrazení/přehrávání i před návratem hledání.
- Nové moduly povplus_policy, povplus_csfd, povplus_store, povplus_catalog.
- Nové routy, hlavní položka a samostatná kategorie nastavení. Výchozí metadata česky.
- Hvězdičky ČSFD u filmů a kontextový detail, filtry přehledu, recenze při dostupnosti.
- Zdrojový build Kodi repozitáře, balíky a testy. Původní kredity zachované.

- Odstraněné zděděné výchozí TMDb/Trakt aplikační přístupové údaje; vlastní údaje se zadávají pouze v nastavení Kodi.
- Párovací kódy/URL se neposílají třetím stranám pro QR obrázky ani zkracování adres a TMDb autorizační URL se neloguje.
- Čtení rating-average, roku z origin a data-review-content sladěno se strukturou ve scraperu SikySikov 3.49. Nejde o převzetí ochranu obcházejícího transportu.

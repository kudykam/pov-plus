# POV+ 0.1.3 · 31. 10. 2026

- Nastavení Metadata nabízí načtení TMDb Read Access Tokenu z TXT souboru na disku, USB nebo dostupné síťové složce přes Kodi VFS.
- Podpora UTF-8/BOM a UTF-16 souborů z Poznámkového bloku, koncového nového řádku a volitelného prefixu Bearer.
- Chybný nebo nečitelný soubor nepřepíše stávající nastavení; token se nevypisuje do hlášek ani logů. Import sám neověřuje platnost na TMDb.

# POV+ 0.1.2 · 31. 10. 2026

- TMDbList při chybějícím API Read Access Tokenu vysvětlí nastavení Metadata. Chyba autorizace ani neplatná odpověď již neskončí tiše.
- Uživatelské hlášky neobsahují tokeny ani obsah odpovědi služby.

# POV+ 0.1.1 · 31. 10. 2026

- Oprava generování odkazů: menu, přehrávání i akce nyní směřují na plugin.video.povplus. Dva obráceně zapsané řetězce z upstreamu odkazovaly na původní POV, což způsobovalo prázdnou novou položku a otevření původních seznamů.
- Cesta vlastních oken používá zdroje POV+ i bez nainstalovaného původního POV.
- Regresní test generuje skutečnou URL menu a předává ji skutečnému routeru; kontroluje i umístění zdrojů oken.
- Po aktualizaci restartuj Kodi, aby se odstranily staré adresy z paměti a obnovil Python runtime.

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

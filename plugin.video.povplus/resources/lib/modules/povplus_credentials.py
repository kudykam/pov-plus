# Modified for POV+ by kudykam · 2026-10-31 · GPL-3.0-only
"""Import a TMDb bearer token locally without displaying or logging its value."""
import re

MAX_BYTES = 16384


def parse_tmdb_token(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('Soubor je příliš velký. Použij textový soubor pouze s tokenem.')
    if isinstance(raw, (bytes, bytearray)):
        encoding = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'
        try:
            raw = bytes(raw).decode(encoding)
        except UnicodeError:
            raise ValueError('Soubor musí být prostý text UTF-8 nebo UTF-16.') from None
    token = raw.strip().lstrip('\ufeff').strip()
    if token.lower().startswith('bearer '):
        token = token[7:].strip()
    if not token:
        raise ValueError('Soubor je prázdný. Vlož do něj API Read Access Token.')
    if re.fullmatch(r'[0-9a-fA-F]{32}', token):
        raise ValueError('Toto vypadá jako API Key. Zkopíruj API Read Access Token.')
    if not re.fullmatch(r'[A-Za-z0-9._~+/-]{20,}={0,}', token):
        raise ValueError('Vlož pouze celý API Read Access Token na jeden řádek, bez uvozovek.')
    return token


def import_tmdb_token(_params=None):
    from modules import kodi_utils as ku
    ku.hide_busy_dialog()
    path = ku.dialog().browseSingle(1, 'Vyber TXT soubor s TMDb tokenem', '', '.txt')
    if not path:
        return False
    try:
        with ku.open_file(path) as source:
            raw = source.readBytes(MAX_BYTES + 1)
        token = parse_tmdb_token(raw)
    except ValueError as error:
        ku.dialog().ok('POV+ · Import TMDb', str(error))
        return False
    except Exception:
        ku.dialog().ok('POV+ · Import TMDb', 'Soubor nelze přečíst. Ověř dostupnost souboru a síťové složky.')
        return False
    try:
        ku.set_setting('tmdb_read_token', token)
        ku.clear_property('povplus_settings')
        ku.make_settings_dict()
    except Exception:
        ku.dialog().ok('POV+ · Import TMDb', 'Token se nepodařilo uložit do nastavení POV+.')
        return False
    ku.dialog().ok('POV+ · Import TMDb',
        'Token byl uložen. Restartuj Kodi a otevři POV+ výběr. '
        'Platnost tokenu se ověří při načtení filmů. Pomocný TXT soubor už není potřeba.')
    return True

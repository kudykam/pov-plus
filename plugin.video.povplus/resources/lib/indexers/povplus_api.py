# Modified for POV+ by kudykam · 2026-10-30 · GPL-3.0-only
import sys
import xbmcvfs

files_path = 'special://home/addons/plugin.video.povplus/lib/povplus/'
povplus_path = xbmcvfs.translatePath('special://home/addons/plugin.video.povplus/lib/')
if povplus_path not in sys.path: sys.path.insert(0, povplus_path)

from povplus import sources
from povplus.modules.client import randomagent
from povplus.modules.health import health
from povplus.modules.undesirables import Undesirables, add_new_default_keywords, undesirablesInput, undesirablesSelect, undesirablesUserRemove


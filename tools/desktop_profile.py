# SPDX-License-Identifier: Apache-2.0
"""Expected persistent tasks for the explicitly selected desktop ROM profile."""
import json
from pathlib import Path

def desktop_task_count(root):
    modules={r['component'] for r in json.loads((Path(root)/'rom-layout.json').read_text())['modules']}
    assert {'Filer','Switcher','Pinboard','ADFSFiler'} <= modules
    # RAMFSFiler is dormant on these cold configurations: RAM disc size is zero.
    return 4+len(modules & {'ResFiler','ArcPalette','Free'})

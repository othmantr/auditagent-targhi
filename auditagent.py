#!/usr/bin/env python3
"""Run the bundled controller without installing dependencies."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).parent / 'plugins/auditagent-targhi/skills/auditagent-targhi/scripts/auditagent.py'), run_name='__main__')

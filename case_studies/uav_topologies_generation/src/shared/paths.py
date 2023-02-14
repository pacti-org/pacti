from __future__ import annotations

import os
from pathlib import Path

this_file = Path(os.path.dirname(__file__))
package_path: Path = this_file.parent

rules_path: Path = package_path / "data" / "rules.json"

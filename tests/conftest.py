"""Make `src` importable before any test module is collected.

Not a convenience. Without it the suite worked by accident: three test modules
inserted this path as an import-time side effect, every other module relied on
one of them having been collected first, and the order that made it true was
alphabetical. A new test file sorting ahead of them failed to import a package
the file beside it imported fine, which is a confusing way to learn this.

CI installs the package (`pip install -e .`) and so never sees it. A working
tree that has not been installed into the running interpreter does.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

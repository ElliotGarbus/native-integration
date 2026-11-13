"""Off-device stub for the `web_views` extension module (PEP 561, sort of).

§7.5: the producer ships this so type checkers and IDEs resolve `web_views`
without the Swift package built. A consumer MUST exclude it from the payload it
assembles for the device -- on device the module is registered before the
interpreter starts, and a `.py` of the same name on `sys.path` would shadow that
registration silently. An import that should have raised ImportError instead
succeeds and does nothing.
"""


def open_url(url: str) -> None:
    raise NotImplementedError("web_views is provided by the PyWebViews Swift package")

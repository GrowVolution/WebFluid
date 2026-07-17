class Version(tuple[int, ...]):
    stage: str
    build: int
    def __init__(
        self, major: str, minor: str | None = None, patch: str | None = None
    ) -> None: ...
    def __new__(
        cls, major: str, minor: str | None = None, patch: str | None = None
    ) -> Version: ...
    def __str__(self) -> str: ...

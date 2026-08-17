from sqlalchemy import MetaData, Table


def _with_driver(uri: str, scheme: str, driver: str) -> str: ...
def database_uris(uri: str) -> tuple[str, str]: ...
def update_metadata(
    table: Table,
    target_md: MetaData | None = None,
    target_bind: str | None = None,
    target_model: type | None = None,
) -> None: ...

from sqlalchemy import MetaData, Table


def database_uris(uri: str) -> tuple[str, str]: ...
def update_metadata(
    table: Table,
    target_md: MetaData | None = None,
    target_bind: str | None = None,
    target_model: type | None = None,
) -> None: ...

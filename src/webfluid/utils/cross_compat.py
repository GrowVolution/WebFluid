from fastapi import Request as FastAPIRequest, UploadFile
from starlette.datastructures import FormData, Headers, QueryParams
from werkzeug.datastructures import FileStorage
from aioflask import Request as FlaskRequest
from frozendict import frozendict
from pathlib import Path
from os import PathLike
import anyio


class RawFile:
    def __init__(self, file: UploadFile | FileStorage):
        self._file = file
        self._fastapi = isinstance(file, UploadFile)
        self.filename = file.filename
        self.content_type = file.content_type

    async def read(self, size: int = -1) -> bytes:
        if self._fastapi: return await self._file.read(size)
        return await anyio.to_thread.run_sync(self._file.stream.read, size)

    async def write(self, data: bytes):
        if self._fastapi: return await self._file.write(data)
        return await anyio.to_thread.run_sync(self._file.stream.write, data)

    async def seek(self, offset: int):
        if self._fastapi: return await self._file.seek(offset)
        return await anyio.to_thread.run_sync(self._file.stream.seek, offset)

    async def save(self, path: Path | PathLike[str] | str):
        file = Path(path)
        file.parent.mkdir(parents=True, exist_ok=True)

        if self._fastapi:
            await self.seek(0)
            async with await anyio.open_file(file, "wb") as f:
                while chunk := await self.read(4096):
                    await f.write(chunk)
        else:
            await anyio.to_thread.run_sync(self._file.save, file)

    async def close(self):
        if self._fastapi: await self._file.close()
        else: await anyio.to_thread.run_sync(self._file.close)


class RawRequest:
    def __init__(self, request: FastAPIRequest | FlaskRequest):
        self._raw = request
        self._fastapi = isinstance(request, FastAPIRequest)

    async def body(self) -> bytes:
        if self._fastapi:
            return await self._raw.body()
        return self._raw.get_data()

    async def json(self) -> frozendict:
        if self._fastapi:
            data = await self._raw.json()
        else: data = self._raw.get_json()
        return frozendict(data or {})

    async def form(self) -> FormData:
        if self._fastapi:
            return await self._raw.form()
        return FormData(self._raw.form)

    async def files(self) -> FormData[str, RawFile]:
        files = {}
        if self._fastapi:
            form = await self._raw.form()
            for key in form.keys():
                values = form.getlist(key)
                upload_files = [RawFile(v) for v in values if isinstance(v, UploadFile)]
                if upload_files: files[key] = upload_files
        else:
            for key in self._raw.files.keys():
                values = self._raw.files.getlist(key)
                upload_files = [RawFile(v) for v in values]
                if upload_files: files[key] = upload_files
        return FormData(files)

    async def stream(self):
        if self._fastapi:
            async for chunk in self._raw.stream():
                yield chunk
        else:
            iterator = self._raw.stream
            while chunk := await anyio.to_thread.run_sync(
                    lambda: next(iterator, None)
            ): yield chunk

    @property
    def headers(self) -> Headers:
        if self._fastapi: return self._raw.headers
        return Headers(self._raw.headers)

    @property
    def cookies(self) -> frozendict:
        return frozendict(self._raw.cookies)

    @property
    def query(self) -> QueryParams:
        if self._fastapi: return self._raw.query_params
        return QueryParams(self._raw.args)

    @property
    def method(self) -> str: return self._raw.method

    @property
    def path(self) -> str:
        if self._fastapi: return self._raw.url.path
        return self._raw.path

    @property
    def scheme(self) -> str:
        if self._fastapi: return self._raw.url.scheme
        return self._raw.scheme

    @property
    def host(self) -> str:
        return self._raw.headers.get("host", "localhost")

    @property
    def client_ip(self) -> str | None:
        if self._fastapi:
            client = self._raw.client
            return client.host if client else None
        return self._raw.remote_addr

    @property
    def url(self) -> str:
        return str(self._raw.url) if self._fastapi else self._raw.url

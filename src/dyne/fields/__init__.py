import os
from typing import BinaryIO, Optional

from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile as BaseFile


class UploadFile(BaseFile):

    def __init__(
        self,
        file: BinaryIO,
        *,
        size: Optional[int] = None,
        filename: Optional[str] = None,
        headers: Optional[Headers] = None,
    ) -> None:
        super().__init__(file, size=size, filename=filename, headers=headers)
        if not self.size:
            self._size()

    async def save(self, destination, buffer_size=16384):
        close_destination = False

        if hasattr(destination, "__fspath__"):
            destination = os.fspath(destination)

        if isinstance(destination, str):
            destination = await run_in_threadpool(open, destination, "wb")
            close_destination = True

        try:
            while True:
                chunk = await self.read(buffer_size)
                if not chunk:
                    break
                await run_in_threadpool(destination.write, chunk)
        finally:
            if close_destination:
                await run_in_threadpool(destination.close)

    def _size(self):
        current_position = self.file.tell()
        self.file.seek(0, os.SEEK_END)
        size = self.file.tell()
        self.file.seek(current_position)
        self.size = size

    @property
    def extension(self) -> str:
        return os.path.splitext(self.filename)[1].lower().strip(".")

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from concurrent.futures import ThreadPoolExecutor

from webfluid.utils.core import run_in_executor


class HashService:
    def __init__(self, time_cost, memory_cost, parallelism, threads=4):
        self._hasher = PasswordHasher(
            time_cost=time_cost, memory_cost=memory_cost,
            parallelism=parallelism
        )
        self._executor = ThreadPoolExecutor(
            max_workers=threads, thread_name_prefix="wf-hash"
        )

    def hash(self, password):
        return self._hasher.hash(password)

    def verify(self, password_hash, password):
        try: return self._hasher.verify(password_hash, password)
        except VerifyMismatchError: return False

    async def ahash(self, password):
        return await run_in_executor(
            self.hash, password, executor=self._executor
        )

    async def averify(self, password_hash, password):
        return await run_in_executor(
            self.verify, password_hash, password, executor=self._executor
        )

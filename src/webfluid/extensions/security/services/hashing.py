from argon2 import PasswordHasher


class HashService:
    def __init__(self, time_cost: int, memory_cost: int, parallelism: int):
        self._hasher = PasswordHasher(
            time_cost=time_cost, memory_cost=memory_cost,
            parallelism=parallelism
        )

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        return self._hasher.verify(password_hash, password)

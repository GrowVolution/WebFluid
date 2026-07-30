from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class HashService:
    def __init__(self, time_cost, memory_cost, parallelism):
        self._hasher = PasswordHasher(
            time_cost=time_cost, memory_cost=memory_cost,
            parallelism=parallelism
        )

    def hash(self, password):
        return self._hasher.hash(password)

    def verify(self, password_hash, password):
        try: return self._hasher.verify(password_hash, password)
        except VerifyMismatchError: return False

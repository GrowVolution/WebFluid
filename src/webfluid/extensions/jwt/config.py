

class JWTConfig:
    def __init__(self, config):
        self.rotary_interval = config["JWT_ROTARY_INTERVAL"]
        self.secret_length = config["JWT_SECRET_LENGTH"]
        self.expiry_days = config["JWT_EXPIRY_DAYS"]
        self.algorithm = config["JWT_ALGORITHM"]
        self.issuer = config["JWT_ISSUER"]
        self.audiences = config["JWT_AUDIENCES"]

    def audience(self, name): return self.audiences.get(name, name)

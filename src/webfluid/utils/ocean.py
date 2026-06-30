from pathlib import Path
import io, tarfile, httpx

from webfluid.core.constants import WF_OCEAN, OCEAN_AUTH
from webfluid.exceptions import OceanError

TOKEN_FILE = Path.home() / ".wf-ocean"

ERROR_MESSAGES = {
    "NOT_AUTHORIZED": "You are not authorized to perform this action.",
    "UNAUTHORIZED": "You are not authorized. Please log in.",
    "NOT_AUTHENTICATED": "You need to log in first. Run 'wf ocean login'.",
    "FORBIDDEN": "You do not have permission to do this.",
    "NOT_FOUND": "The requested resource was not found.",
    "VALIDATION_ERROR": "The request was invalid.",
    "LOGIN_REQUIRED": "You need to log in first. Run 'wf ocean login'.",
    "OWNERSHIP_REQUIRED": "You need to own this package first.",
    "INVALID_TOKEN": "The token is invalid or expired.",
    "TOKEN_EXPIRED": "Your token has expired. Please log in again.",
    "NO_OCEAN_GRANT": "This token has no Ocean grants.",
    "NO_OCEAN_ACCESS": "This account has no access to the Ocean.",
    "UNKNOWN_USER": "The token's user could not be found.",
    "PACKAGE_NOT_FOUND": "The package could not be found.",
    "UNKNOWN_PACKAGE": "The package could not be found.",
    "UNKNOWN_PACKAGE_TYPE": "Unknown package type.",
    "UNKNOWN_RELEASE": "The requested release could not be found.",
    "PACKAGE_ALREADY_INSTALLED": "A package with this id is already installed.",
    "PACKAGE_EXISTS": "A package with this id already exists.",
    "RELEASE_EXISTS": "This release version already exists.",
    "WITHDRAWAL_WAIVER_REQUIRED": "You must waive your right of withdrawal before downloading this package.",
    "PRICE_REQUIRED": "Extensions must have a price.",
    "STRIPE_NOT_ONBOARDED": "The selected maintainer is not onboarded for payments.",
    "CHECKSUM_MISMATCH": "Upload integrity check failed.",
    "EMPTY_BODY": "The package archive is empty.",
    "MISSING_MANIFEST": "The additive is missing a manifest.json.",
    "MISSING_PYPROJECT": "The extension is missing a pyproject.toml.",
    "INVALID_META": "The package metadata is invalid.",
    "ID_MISMATCH": "The package id does not match the existing package.",
    "CLONE_FAILED": "The repository could not be cloned.",
    "NOT_ENROLLED": "You are not enrolled as a publisher.",
    "UNKNOWN_ERROR": "An unknown error occurred."
}


def humanize_error(detail, fallback=None):
    if not detail:
        return fallback or ERROR_MESSAGES["UNKNOWN_ERROR"]
    if detail in ERROR_MESSAGES:
        return ERROR_MESSAGES[detail]
    if isinstance(detail, str) and detail.isupper():
        return f"{fallback or 'The Ocean reported an error'} ({detail})."
    return detail


def token_file():
    return TOKEN_FILE


def load_token():
    if not TOKEN_FILE.exists(): return None
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    return token or None


def save_token(token):
    TOKEN_FILE.write_text(token.strip(), encoding="utf-8")


def delete_token():
    if not TOKEN_FILE.exists(): return False
    TOKEN_FILE.unlink()
    return True


def extract_archive(data, target):
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        tar.extractall(target, filter="data")


class Ocean:
    def __init__(self, token=None, base_url=WF_OCEAN, auth_url=OCEAN_AUTH):
        self.base_url = base_url.rstrip("/")
        self.auth_url = auth_url.rstrip("/")
        self.token = token if token is not None else load_token()

    @property
    def authenticated(self):
        return bool(self.token)

    def _headers(self, extra=None):
        headers = {}
        if self.token: headers["Authorization"] = f"Bearer {self.token}"
        if extra: headers.update(extra)
        return headers

    def _request(self, method, path, base=None, **kwargs):
        url = f"{base or self.base_url}{path}"
        headers = self._headers(kwargs.pop("headers", None))
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError as e:
            raise OceanError(0, f"Could not reach the Ocean: {e}")
        return self._parse(response)

    @staticmethod
    def _detail(data):
        if not isinstance(data, dict): return None
        detail = data.get("detail") or data.get("message") or data.get("error")
        if isinstance(detail, dict):
            for field in ("code", "key", "i18n_key", "message", "detail"):
                value = detail.get(field)
                if value: return value
            return None
        return detail

    @staticmethod
    def _parse(response):
        content_type = response.headers.get("content-type", "")
        data = response.json() if content_type.startswith("application/json") \
            else response.content

        if response.status_code >= 400:
            raise OceanError(
                response.status_code,
                Ocean._detail(data) or "UNKNOWN_ERROR"
            )

        return data

    def search(self, q="", types=None, license=""):
        params = {"q": q}
        if types: params["type"] = ",".join(types)
        if license: params["license"] = license
        return self._request("GET", "/cli/search", params=params)["items"]

    def resolve(self, ptype, package_id):
        return self._request("GET", f"/cli/packages/{ptype}/{package_id}")

    def download(self, ptype, package_id, version):
        return self._request(
            "GET", f"/download/{ptype}/{package_id}/{version}"
        )

    def waive(self, ptype, package_id):
        return self._request("POST", f"/download/{ptype}/{package_id}/waiver")

    def login_check(self):
        return self._request("GET", "/cli/auth")

    def token_info(self):
        return self._request(
            "GET", "/users/jwt/metadata", base=self.auth_url
        )

    def maintainers(self):
        return self._request("GET", "/enroll")

    def publish(self, ptype, data, checksum, orga=None, price=None):
        params = {}
        if orga is not None: params["orga"] = orga
        if price is not None: params["price"] = price
        return self._request(
            "POST", f"/publish/{ptype}/upload",
            params=params, content=data,
            headers={
                "Content-Type": "application/octet-stream",
                "X-Content-SHA256": checksum
            }
        )

    def license_search(self, q=""):
        return self._request("GET", "/licenses", params={"q": q})

    def license_placeholders(self, ptype, package_id, license_id):
        return self._request(
            "GET", f"/packages/{ptype}/{package_id}/license/placeholders",
            params={"license_id": license_id}
        )

    def select_license(self, ptype, package_id, license_id, values):
        return self._request(
            "POST", f"/packages/{ptype}/{package_id}/license",
            json={"license_id": license_id, "values": values}
        )

from email.mime.multipart import MIMEMultipart


def make_message(
    default_sender: str, to: str, subject: str, body: dict[str, str],
    attachments: list[dict[str, bytes | str]] | None = None,
    from_email: str | None = None, cc: list[str] | None = None,
    bcc: list[str] | None = None
) -> MIMEMultipart: ...

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from webfluid.exceptions import FrameworkException


def make_message(default_sender, to, subject, body,
                 attachments=None, from_email=None, cc=None, bcc=None):
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = from_email or default_sender
        msg["To"] = to
        if cc: msg["Cc"] = ", ".join(cc)
        if bcc: msg["Bcc"] = ", ".join(bcc)
        msg["Subject"] = subject

        for t, content in body.items():
            msg.attach(MIMEText(content, t, "utf-8"))

        if attachments:
            for attachment in attachments:
                data = attachment["bytes"]
                data = data if isinstance(data, bytes) else data.encode("utf-8")
                application = MIMEApplication(
                    data, attachment["type"]
                )
                application.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment["filename"]
                )
                msg.attach(application)
    except KeyError as e:
        raise FrameworkException(f"Failed to send mail: {e}")

    return msg

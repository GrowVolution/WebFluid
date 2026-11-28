from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid, parseaddr

from webfluid.exceptions import FrameworkException


def _domain(sender) -> str:
    address = parseaddr(str(sender or ""))[1]
    return address.rpartition("@")[2] or "localhost"


def make_message(default_sender, to, subject, body,
                 attachments=None, from_email=None, cc=None, bcc=None):
    try:
        alternative = MIMEMultipart("alternative")
        for t, content in body.items():
            alternative.attach(MIMEText(content, t, "utf-8"))

        if attachments:
            msg = MIMEMultipart("mixed")
            msg.attach(alternative)
        else:
            msg = alternative

        msg["From"] = from_email or default_sender
        msg["To"] = to
        if cc: msg["Cc"] = ", ".join(cc)
        if bcc: msg["Bcc"] = ", ".join(bcc)
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=False, usegmt=True)
        msg["Message-ID"] = make_msgid(domain=_domain(msg["From"]))

        if attachments:
            for attachment in attachments:
                data = attachment["bytes"]
                data = data if isinstance(data, bytes) else data.encode("utf-8")
                kind = str(attachment["type"])
                maintype, subtype = kind.split("/", 1) if "/" in kind else ("application", kind)
                part = MIMEBase(maintype, subtype)
                part.set_payload(data)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment["filename"]
                )
                msg.attach(part)
    except KeyError as e:
        raise FrameworkException(f"Failed to send mail: {e}")

    return msg

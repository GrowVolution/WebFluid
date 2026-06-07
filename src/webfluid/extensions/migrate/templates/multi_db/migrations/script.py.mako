"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()

<%
    from webfluid.core.ext import db
    bind_names = [b for b in db.bind_keys if b != "default"]
    db_names = ["default"] + bind_names
%>

## generate an "upgrade_<xyz>() / downgrade_<xyz>()" function
## for each bind key in the config.

% for db_name in db_names:

def upgrade_${db_name}():
    ${context.get("%s_upgrades" % db_name, "pass")}


def downgrade_${db_name}():
    ${context.get("%s_downgrades" % db_name, "pass")}

% endfor

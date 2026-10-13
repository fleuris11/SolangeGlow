from django.db import migrations

# The ledger is append-only: even a mistake in the code or in the database console cannot
# change or delete an entry (corrections are new entries). ADR-007.
FORBID = """
CREATE OR REPLACE FUNCTION payments_ledger_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'The ledger is append-only (%), write a correcting entry instead.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER payments_journalentry_append_only
    BEFORE UPDATE OR DELETE ON payments_journalentry
    FOR EACH ROW EXECUTE FUNCTION payments_ledger_append_only();

CREATE TRIGGER payments_journalline_append_only
    BEFORE UPDATE OR DELETE ON payments_journalline
    FOR EACH ROW EXECUTE FUNCTION payments_ledger_append_only();
"""

ALLOW = """
DROP TRIGGER IF EXISTS payments_journalline_append_only ON payments_journalline;
DROP TRIGGER IF EXISTS payments_journalentry_append_only ON payments_journalentry;
DROP FUNCTION IF EXISTS payments_ledger_append_only();
"""


class Migration(migrations.Migration):
    dependencies = [("payments", "0001_initial")]

    operations = [migrations.RunSQL(FORBID, ALLOW)]

from django.db import migrations

# The points ledger is append-only, like the money ledger (ADR-007): a gain or a spending
# is never changed or deleted; a correction is a new entry. ADR-015.
FORBID = """
CREATE OR REPLACE FUNCTION gamification_points_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'The points ledger is append-only (%), write a correcting entry instead.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER gamification_pointsentry_append_only
    BEFORE UPDATE OR DELETE ON gamification_pointsentry
    FOR EACH ROW EXECUTE FUNCTION gamification_points_append_only();
"""

ALLOW = """
DROP TRIGGER IF EXISTS gamification_pointsentry_append_only ON gamification_pointsentry;
DROP FUNCTION IF EXISTS gamification_points_append_only();
"""


class Migration(migrations.Migration):
    dependencies = [("gamification", "0001_initial")]

    operations = [migrations.RunSQL(FORBID, ALLOW)]

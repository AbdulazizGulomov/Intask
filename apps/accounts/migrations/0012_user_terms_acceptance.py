# Terms/EULA acceptance fields (App Store Guideline 1.2).
#
# Scoped to the two new User columns on purpose. `makemigrations` also wants to
# drop WorkerProfile.certificate here — that column is pre-existing drift
# (migration 0007 added it; the model dropped the field without a migration,
# before this branch). Dropping a FileField column is destructive and unrelated
# to UGC safety, so it is deliberately left for its own migration.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_workerprofile_lat_lng"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="terms_accepted_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Terms accepted at"
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="terms_version",
            field=models.CharField(
                blank=True, default="", max_length=20, verbose_name="Accepted terms version"
            ),
        ),
    ]

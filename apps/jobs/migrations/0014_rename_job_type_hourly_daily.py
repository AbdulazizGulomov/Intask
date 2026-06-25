# Rename job_type choices doimiy/vaqtinchalik -> hourly/daily, and remap existing rows.
#
# NOTE: the autodetector also wanted to "RemoveField profession from job" — that is a
# PRE-EXISTING model/migration drift unrelated to this change and dropping a column is
# destructive, so it is intentionally NOT included here.

from django.db import migrations, models


def remap_forwards(apps, schema_editor):
    """doimiy -> hourly, vaqtinchalik -> daily. Anything unexpected -> daily (fail-safe)."""
    Job = apps.get_model("jobs", "Job")
    Job.objects.filter(job_type="doimiy").update(job_type="hourly")
    Job.objects.filter(job_type="vaqtinchalik").update(job_type="daily")
    # Guarantee zero invalid rows: coerce any leftover value to "daily".
    Job.objects.exclude(job_type__in=["hourly", "daily"]).update(job_type="daily")


def remap_backwards(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    Job.objects.filter(job_type="hourly").update(job_type="doimiy")
    Job.objects.filter(job_type="daily").update(job_type="vaqtinchalik")


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0013_alter_job_job_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="job_type",
            field=models.CharField(
                choices=[("hourly", "Hourly"), ("daily", "Daily")], max_length=20
            ),
        ),
        migrations.RunPython(remap_forwards, remap_backwards),
    ]

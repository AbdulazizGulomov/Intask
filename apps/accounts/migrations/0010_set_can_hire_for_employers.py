# Data migration: existing employers keep the ability to post jobs after the
# move to capability-based gating. Sets can_hire=True where role == "employer".
from django.db import migrations


def set_can_hire_for_employers(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='employer').update(can_hire=True)


def unset_can_hire(apps, schema_editor):
    # Reverse: drop the flag back to the AddField default for employers.
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='employer').update(can_hire=False)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_user_can_hire'),
    ]

    operations = [
        migrations.RunPython(set_can_hire_for_employers, unset_can_hire),
    ]

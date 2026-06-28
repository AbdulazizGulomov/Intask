# Adds the dual-mode capability flag. Schema-only (AddField); the data backfill
# for existing employers lives in 0010_set_can_hire_for_employers.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_alter_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='can_hire',
            field=models.BooleanField(default=False),
        ),
    ]

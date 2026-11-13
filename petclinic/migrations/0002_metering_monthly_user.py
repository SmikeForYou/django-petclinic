from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('petclinic', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='MeteringMonthlyUser',
            fields=[
                ('id', models.AutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID',
                )),
                ('year_month', models.CharField(max_length=7)),
                ('identity_hash', models.CharField(max_length=64)),
                ('first_seen', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'unique_together': {('year_month', 'identity_hash')},
            },
        ),
        migrations.AddIndex(
            model_name='meteringmonthlyuser',
            index=models.Index(
                fields=['year_month'],
                name='petclinic_m_year_mo_idx',
            ),
        ),
    ]

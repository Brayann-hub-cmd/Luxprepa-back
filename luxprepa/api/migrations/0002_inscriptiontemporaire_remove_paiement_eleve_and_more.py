import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='InscriptionTemporaire',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('nom', models.CharField(max_length=100)),
                ('prenom', models.CharField(max_length=100)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('telephone', models.CharField(max_length=20, unique=True)),
                ('password_hash', models.CharField(max_length=255)),
                ('role', models.CharField(choices=[('admin', 'Admin'), ('eleve', 'Élève'), ('prof', 'Professeur')], max_length=20)),
                ('date_naissance', models.DateField(blank=True, null=True)),
                ('tel_parent', models.CharField(blank=True, max_length=20, null=True)),
                ('specialite', models.CharField(blank=True, max_length=100, null=True)),
                ('code_sms', models.CharField(max_length=6)),
                ('code_expire_at', models.DateTimeField()),
                ('tentatives', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'inscriptions_temporaires',
            },
        ),
        migrations.RemoveField(
            model_name='paiement',
            name='eleve',
        ),
        migrations.AlterField(
            model_name='paiement',
            name='inscription',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='paiements', to='api.inscription'),
        ),
        migrations.AlterField(
            model_name='paiement',
            name='statut',
            field=models.CharField(choices=[('en_attente', 'En attente'), ('en_cours', 'En cours'), ('paye', 'Payé'), ('echoue', 'Échoué')], default='en_attente', max_length=20),
        ),
    ]

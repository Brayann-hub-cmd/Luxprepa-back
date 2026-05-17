import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class User(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('eleve', 'Élève'),
        ('prof', 'Professeur'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=False, null=False)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def verifier_password(self, raw_password):
        return check_password(raw_password, self.password)

    def se_connecter(self):
        pass

    def signup(self):
        pass


class Admin(User):
    class Meta:
        db_table = 'administrateurs'

    def __str__(self):
        return f"Admin: {self.prenom} {self.nom}"


class Eleve(User):
    date_naissance = models.DateField(null=True, blank=True)
    tel_parent = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        db_table = 'eleves'

    def __str__(self):
        return f"Élève: {self.prenom} {self.nom}"

    def composer(self):
        pass


class Prof(User):
    specialite = models.CharField(max_length=100)

    class Meta:
        db_table = 'professeurs'

    def __str__(self):
        return f"Prof: {self.prenom} {self.nom} ({self.specialite})"

    def noter(self):
        pass


class Matiere(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'matieres'

    def __str__(self):
        return self.nom


class Concours(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    inscription_prepa = models.IntegerField(default=0)
    montant_prepa = models.IntegerField(default=0)
    date_debut = models.DateField(editable=True)
    date_fin = models.DateField(editable=True)
    matieres = models.ManyToManyField(
        Matiere,
        through='MatiereConcours',
        related_name='concours'
    )

    class Meta:
        db_table = 'concours'

    def __str__(self):
        return self.nom

    def concours(self):
        pass


class MatiereConcours(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    matiere = models.ForeignKey(Matiere, on_delete=models.CASCADE, related_name='matiere_concours')
    concours = models.ForeignKey(Concours, on_delete=models.CASCADE, related_name='matiere_concours')
    coefficient = models.IntegerField(default=1)

    class Meta:
        db_table = 'matiere_concours'
        unique_together = ('matiere', 'concours')

    def __str__(self):
        return f"{self.matiere.nom} - {self.concours.nom} (coeff: {self.coefficient})"


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=200)
    date = models.DateField()
    concours = models.ForeignKey(
        Concours,
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'sessions'

    def __str__(self):
        return f"{self.nom} ({self.date})"


class Inscription(models.Model):
    STATUS_CHOICES = [
        ('en_attente', 'En attente'),
        ('validee', 'Validée'),
        ('rejetee', 'Rejetée'),
        ('annulee', 'Annulée'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='inscriptions')
    concours = models.ForeignKey(Concours, on_delete=models.CASCADE, related_name='inscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='en_attente')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inscriptions'
        unique_together = ('eleve', 'concours')

    def __str__(self):
        return f"{self.eleve} -> {self.concours} ({self.status})"


class Paiement(models.Model):
    STATUT_CHOICES = [
        (0, 'En attente'),
        (1, 'En cours'),
        (2, 'Payé'),
        (3, 'Échoué'),
        (4, 'Remboursé'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.CASCADE,
        related_name='paiements',
        null=True,
        blank=True
    )
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='paiements')
    statut = models.IntegerField(choices=STATUT_CHOICES, default=0)
    montant = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paiements'

    def __str__(self):
        return f"Paiement {self.montant} FCFA - {self.get_statut_display()}"


class Annonce(models.Model):
    TYPE_CHOICES = [
        ('info', 'Information'),
        ('alerte', 'Alerte'),
        ('resultat', 'Résultat'),
        ('autre', 'Autre'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, related_name='annonces')
    titre = models.CharField(max_length=255)
    contenu = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'annonces'

    def __str__(self):
        return self.titre


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='notes')
    prof = models.ForeignKey(Prof, on_delete=models.SET_NULL, null=True, related_name='notes')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='notes')
    matiere_concours = models.ForeignKey(
        MatiereConcours,
        on_delete=models.CASCADE,
        related_name='notes',
        null=True,
        blank=True
    )
    valeur = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notes'

    def __str__(self):
        return f"{self.eleve} - {self.valeur}/20"
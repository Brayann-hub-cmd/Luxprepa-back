import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta

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
        ordering = ['-nom']

    def __str__(self):
        return f"{self.prenom} {self.nom}"

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith('pbkdf2_'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
 
    def save_without_hashing(self, *args, **kwargs):
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
    NIVEAU_CHOICES = [
        ('tle','Terminale'),
        ('post_bac', 'Post-Bacc')
    ]
    date_naissance = models.DateField(null=True, blank=True)
    tel_parent = models.CharField(max_length=20, blank=True, null=True)
    niveau = models.CharField(max_length=20,choices=NIVEAU_CHOICES,null=True,blank=True)
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

class InscriptionTemporaire(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('eleve', 'Élève'),
        ('prof', 'Professeur'),
    ]
 
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=20, unique=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
 
    # Champs spécifiques élève
    date_naissance = models.DateField(null=True, blank=True)
    tel_parent = models.CharField(max_length=20, blank=True, null=True)
    niveau = models.CharField(max_length=20,blank=True,null=True)
    # Champs spécifiques prof
    specialite = models.CharField(max_length=100, blank=True, null=True)
 
    # Code de confirmation
    code_sms = models.CharField(max_length=6)
    code_expire_at = models.DateTimeField()  
    tentatives = models.IntegerField(default=0)
 
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = 'inscriptions_temporaires'
 
    def est_expire(self):
        return timezone.now() > self.code_expire_at
 
    def trop_de_tentatives(self):
        return self.tentatives >= 3
 
    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.telephone})"

class Matiere(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'matieres'
        ordering = ['-nom']

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
        ordering = ['-nom']

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
    eleve = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inscriptions')
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
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),      
        ('paye', 'Payé'),              
        ('echoue', 'Échoué'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inscription = models.ForeignKey(
        Inscription,
        on_delete=models.CASCADE,
        related_name='paiements'
    )
    montant = models.IntegerField() 
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='en_attente'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paiements'
        ordering = ['-created_at']

    def __str__(self):
        return f"Paiement {self.montant} FCFA - {self.get_statut_display()}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.mettre_a_jour_statut()

    def mettre_a_jour_statut(self):
        concours = self.inscription.concours

        # Somme de tous les versements pour cette inscription
        from django.db.models import Sum
        total_paye = Paiement.objects.filter(
            inscription=self.inscription
        ).aggregate(Sum('montant'))['montant__sum'] or 0

        # Déterminer le statut selon le total payé
        if total_paye >= concours.montant_prepa + concours.inscription_prepa:
            nouveau_statut = 'paye'
        elif total_paye >= concours.inscription_prepa:
            nouveau_statut = 'en_cours'
        else:
            nouveau_statut = 'en_attente'

        # Mettre à jour sans rappeler save() pour éviter la récursion
        Paiement.objects.filter(id=self.id).update(statut=nouveau_statut)


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
    image = models.ImageField(upload_to='annonces/',null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'annonces'
        ordering = ['-created_at']

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
        unique_together = ('eleve', 'session', 'matiere_concours')
        db_table = 'notes'

class Activite(models.Model):
    TYPE_CHOICES = [
        ('inscription','Inscription'),
        ('paiement','Paiement'),
        ('note','Note'),
        ('annonce','Annonce'),
        ('compte','Compte')
    ]

    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    type_act = models.CharField(max_length=20,choices=TYPE_CHOICES)
    message = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'activites'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.type} - {self.message}'
    
class LienResultat(models.Model):
    token = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='liens_resultats')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='liens_resultats')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('eleve', 'session')
        db_table = 'liens_resultats'

    def est_valide(self):
        if self.date_expiration and timezone.now() > self.date_expiration:
            return False
        return True

    def __str__(self):
        return f"Lien {self.eleve} - {self.session}"
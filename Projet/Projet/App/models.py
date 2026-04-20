from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.conf import settings
import os

# Create your models here.

class User(AbstractUser):
    """Modèle utilisateur étendu avec accès basé sur les rôles"""
    ROLE_CHOICES = [
        ('parent', 'Parent'),
        ('intervenant', 'Intervenant/Éclaireur'),
        ('professeur', 'Professeur'),
        ('admin', 'Administrateur'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='parent', verbose_name='Rôle')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    is_validated = models.BooleanField(default=False, verbose_name='Validé')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    establishment = models.ForeignKey(
        'Establishment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
        verbose_name='Établissement',
        help_text='Établissement de rattachement (principalement pour les professeurs et intervenants)'
    )
    
    # Fix related_name conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="custom_user_set",
        related_query_name="custom_user",
    )
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

class Establishment(models.Model):
    """Établissements scolaires partenaires"""
    name = models.CharField(max_length=200, verbose_name='Nom')
    address = models.TextField(verbose_name='Adresse')
    city = models.CharField(max_length=100, verbose_name='Ville')
    postal_code = models.CharField(max_length=10, verbose_name='Code postal')
    region = models.CharField(max_length=100, verbose_name='Région')
    school_type = models.CharField(max_length=50, verbose_name='Type d\'établissement')  # lycée, collège, etc.
    contact_email = models.EmailField(verbose_name='Email de contact')
    contact_phone = models.CharField(max_length=20, verbose_name='Téléphone de contact')
    is_partner = models.BooleanField(default=False, verbose_name='Partenaire')
    partnership_date = models.DateField(null=True, blank=True, verbose_name='Date de partenariat')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    
    class Meta:
        verbose_name = 'Établissement'
        verbose_name_plural = 'Établissements'
    
    def __str__(self):
        return self.name

class Room(models.Model):
    """Modèle pour les salles des établissements"""
    name = models.CharField(max_length=100, verbose_name='Nom de la salle')
    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='rooms', verbose_name='Établissement')
    capacity = models.PositiveIntegerField(null=True, blank=True, verbose_name='Capacité')
    description = models.TextField(blank=True, verbose_name='Description')
    is_available = models.BooleanField(default=True, verbose_name='Disponible')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    
    class Meta:
        verbose_name = 'Salle'
        verbose_name_plural = 'Salles'
    
    def __str__(self):
        return f"{self.name} - {self.establishment.name}"

class Student(models.Model):
    """Modèle étudiant pour les étudiants inscrits"""
    first_name = models.CharField(max_length=100, verbose_name='Prénom')
    last_name = models.CharField(max_length=100, verbose_name='Nom')
    email = models.EmailField(blank=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Téléphone')
    birth_date = models.DateField(verbose_name='Date de naissance')
    parent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='children', verbose_name='Parent')
    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='students', verbose_name='Établissement')
    professor = models.CharField(max_length=100, blank=True, verbose_name='Professeur')
    classe = models.CharField(max_length=50, blank=True, verbose_name='Classe')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    
    class Meta:
        verbose_name = 'Étudiant'
        verbose_name_plural = 'Étudiants'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Level(models.Model):
    """Modèle pour les niveaux scolaires"""
    name = models.CharField(max_length=50, unique=True, verbose_name='Nom du niveau')
    order = models.PositiveIntegerField(default=0, verbose_name='Ordre')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    
    class Meta:
        verbose_name = 'Niveau'
        verbose_name_plural = 'Niveaux'
        ordering = ['order']
    
    def __str__(self):
        return self.name

class Workshop(models.Model):
    """Modèle atelier/workshop"""
    
    # Choices for days of the week
    MONDAY = 'monday'
    TUESDAY = 'tuesday'
    WEDNESDAY = 'wednesday'
    THURSDAY = 'thursday'
    FRIDAY = 'friday'
    SATURDAY = 'saturday'
    
    DAY_CHOICES = [
        (MONDAY, 'Lundi'),
        (TUESDAY, 'Mardi'),
        (WEDNESDAY, 'Mercredi'),
        (THURSDAY, 'Jeudi'),
        (FRIDAY, 'Vendredi'),
        (SATURDAY, 'Samedi'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='Titre')
    description = models.TextField(verbose_name='Description')
    establishment = models.ForeignKey(Establishment, on_delete=models.CASCADE, related_name='workshops', verbose_name='Établissement')
    intervenant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='workshops', verbose_name='Intervenant')
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='workshops', verbose_name='Salle')
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True, related_name='workshops', verbose_name='Niveau')
    day = models.CharField(
        max_length=10,
        choices=DAY_CHOICES,
        default=MONDAY,
        verbose_name='Jour de la semaine',
        help_text='Jour de la semaine où se déroule l\'atelier'
    )
    max_students = models.PositiveIntegerField(verbose_name='Nombre maximum d\'étudiants')
    start_date = models.DateTimeField(verbose_name='Date de début')
    end_date = models.DateTimeField(verbose_name='Date de fin')
    is_active = models.BooleanField(default=True, verbose_name='Actif')
    is_recurrent = models.BooleanField(
        default=True, 
        verbose_name='Atelier récurrent',
        help_text='Si coché, l\'atelier se répète chaque semaine au jour indiqué jusqu\'à la date de fin. Sinon, l\'atelier est ponctuel (une seule occurrence).'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    
    class Meta:
        verbose_name = 'Atelier'
        verbose_name_plural = 'Ateliers'
    
    def __str__(self):
        return f"{self.title} - {self.establishment.name}"

class Enrollment(models.Model):
    """Inscription des étudiants aux ateliers"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments', verbose_name='Étudiant')
    workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name='enrollments', verbose_name='Atelier')
    enrollment_date = models.DateTimeField(auto_now_add=True, verbose_name='Date d\'inscription')
    is_confirmed = models.BooleanField(default=False, verbose_name='Confirmé')
    
    class Meta:
        unique_together = ['student', 'workshop']
        verbose_name = 'Inscription'
        verbose_name_plural = 'Inscriptions'
    
    def __str__(self):
        return f"{self.student} - {self.workshop.title}"
    
    def get_attendance_rate(self, days=30):
        """Calculate attendance rate for the last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now().date() - timedelta(days=days)
        attendances = self.attendances.filter(date__gte=cutoff_date)
        
        total = attendances.count()
        if total == 0:
            return 0
        
        present = attendances.filter(status__in=['present', 'late']).count()
        return round((present / total) * 100, 1)

class ParentApplication(models.Model):
    """Demandes d'inscription des parents/étudiants"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    
    parent_first_name = models.CharField(max_length=100, verbose_name='Prénom du parent')
    parent_last_name = models.CharField(max_length=100, verbose_name='Nom du parent')
    parent_email = models.EmailField(verbose_name='Email du parent')
    parent_phone = models.CharField(max_length=20, verbose_name='Téléphone du parent')
    # Legacy fields for backward compatibility (will be deprecated)
    student_first_name = models.CharField(max_length=100, verbose_name='Prénom de l\'étudiant', blank=True, null=True)
    student_last_name = models.CharField(max_length=100, verbose_name='Nom de l\'étudiant', blank=True, null=True)
    student_birth_date = models.DateField(verbose_name='Date de naissance de l\'étudiant', blank=True, null=True)
    # New field for multiple students
    students = models.JSONField(verbose_name='Étudiants', default=list, blank=True, 
                                help_text='Liste des étudiants au format JSON: [{"first_name": "", "last_name": "", "birth_date": "YYYY-MM-DD"}]')
    school_name = models.CharField(max_length=200, verbose_name='Nom de l\'école')
    motivation = models.TextField(verbose_name='Motivation', blank=True)
    wants_to_donate = models.BooleanField(default=False, verbose_name='Souhaite faire un don', 
                                         help_text='Le parent souhaite-t-il faire un don ?')
    donation_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                         verbose_name='Montant du don', 
                                         help_text='Montant du don souhaité en euros')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Statut')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Date de traitement')
    
    class Meta:
        verbose_name = 'Demande Parent'
        verbose_name_plural = 'Demandes Parents'
    
    def __str__(self):
        return f"Demande {self.parent_first_name} {self.parent_last_name}"
    
    def get_students(self):
        """Retourne la liste des étudiants (nouveau format ou legacy)"""
        if self.students:
            return self.students
        # Fallback to legacy fields if students list is empty
        if self.student_first_name and self.student_last_name:
            return [{
                'first_name': self.student_first_name,
                'last_name': self.student_last_name,
                'birth_date': self.student_birth_date.isoformat() if self.student_birth_date else None
            }]
        return []

class PartnerApplication(models.Model):
    """Demandes de partenariat scolaire"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    
    school_name = models.CharField(max_length=200, verbose_name='Nom de l\'école')
    contact_name = models.CharField(max_length=200, verbose_name='Nom du contact')
    contact_email = models.EmailField(verbose_name='Email de contact')
    contact_phone = models.CharField(max_length=20, verbose_name='Téléphone de contact')
    school_address = models.TextField(verbose_name='Adresse de l\'école')
    motivation = models.TextField(verbose_name='Motivation')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Statut')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Date de traitement')
    
    class Meta:
        verbose_name = 'Demande Partenariat'
        verbose_name_plural = 'Demandes Partenariats'
    
    def __str__(self):
        return f"Partenariat {self.school_name}"

class IntervenantApplication(models.Model):
    """Demandes de candidature pour devenir intervenant"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    
    # Informations personnelles
    prenom = models.CharField(max_length=100, verbose_name='Prénom')
    nom = models.CharField(max_length=100, verbose_name='Nom')
    email = models.EmailField(verbose_name='Email')
    telephone = models.CharField(max_length=20, verbose_name='Téléphone')
    date_naissance = models.DateField(verbose_name='Date de naissance')
    adresse = models.CharField(max_length=300, verbose_name='Adresse')
    
    # Formation et expérience
    niveau_etudes = models.CharField(max_length=50, verbose_name='Niveau d\'études')
    domaine_etudes = models.CharField(max_length=200, verbose_name='Domaine d\'études')
    experience = models.CharField(max_length=50, verbose_name='Expérience', blank=True)
    matieres = models.TextField(verbose_name='Matières')
    
    # Disponibilités
    disponibilites = models.TextField(verbose_name='Disponibilités')
    heures_semaine = models.CharField(max_length=50, verbose_name='Heures par semaine')
    
    # Motivation
    motivation = models.TextField(verbose_name='Motivation')
    
    # Documents
    cv = models.FileField(upload_to='intervenants/cv/', verbose_name='CV')
    autre_documents = models.FileField(upload_to='intervenants/autres/', blank=True, null=True, verbose_name='Autre documents')
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Statut')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Date de traitement')
    
    class Meta:
        verbose_name = 'Candidature Intervenant'
        verbose_name_plural = 'Candidatures Intervenants'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Candidature {self.prenom} {self.nom}"

class Document(models.Model):
    """Modèle pour les documents partagés par les intervenants"""
    DOCUMENT_TYPE_CHOICES = [
        ('cours', 'Cours'),
        ('exercice', 'Exercice'),
        ('ressource', 'Ressource'),
        ('devoir', 'Devoir'),
        ('corrige', 'Corrigé'),
        ('autre', 'Autre'),
    ]
    
    title = models.CharField(max_length=200, verbose_name='Titre')
    description = models.TextField(blank=True, verbose_name='Description')
    file = models.FileField(upload_to='documents/%Y/%m/%d/', verbose_name='Fichier')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES, default='autre', verbose_name='Type de document')
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents', verbose_name='Intervenant')
    workshops = models.ManyToManyField(Workshop, related_name='documents', verbose_name='Ateliers')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Date d\'upload')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Date de modification')
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='Taille du fichier (bytes)')
    
    class Meta:
        verbose_name = 'Document'
        verbose_name_plural = 'Documents'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.title} - {self.uploader.get_full_name() or self.uploader.username}"
    
    def save(self, *args, **kwargs):
        # Calculate file size when saving
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def get_file_size_display(self):
        """Return human-readable file size"""
        if not self.file_size:
            return "0 B"
        size = float(self.file_size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"

class AttendanceSheet(models.Model):
    """Feuille de présence pour un atelier à une date donnée"""
    workshop = models.ForeignKey(
        Workshop,
        on_delete=models.CASCADE,
        related_name='attendance_sheets',
        verbose_name='Atelier'
    )
    date = models.DateField(verbose_name='Date de la séance')
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_attendance_sheets',
        verbose_name='Créé par'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Dernière modification')
    notes = models.TextField(blank=True, verbose_name='Notes de la séance')
    is_finalized = models.BooleanField(default=False, verbose_name='Finalisée')
    
    class Meta:
        unique_together = ['workshop', 'date']
        verbose_name = 'Feuille de présence'
        verbose_name_plural = 'Feuilles de présence'
        ordering = ['-date']
        indexes = [
            models.Index(fields=['workshop', 'date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.workshop.title} - {self.date.strftime('%d/%m/%Y')}"

class Attendance(models.Model):
    """Présence d'un étudiant dans une feuille de présence"""
    STATUS_CHOICES = [
        ('present', 'Présent'),
        ('absent', 'Absent'),
    ]
    
    attendance_sheet = models.ForeignKey(
        AttendanceSheet,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='Feuille de présence',
        null=True,  # Temporarily nullable for migration
        blank=True
    )
    enrollment = models.ForeignKey(
        Enrollment, 
        on_delete=models.CASCADE, 
        related_name='attendances', 
        verbose_name='Inscription'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='absent', 
        verbose_name='Statut'
    )
    notes = models.TextField(blank=True, verbose_name='Notes/Commentaires')
    marked_at = models.DateTimeField(auto_now=True, verbose_name='Date de marquage')
    
    class Meta:
        unique_together = ['attendance_sheet', 'enrollment']
        verbose_name = 'Présence'
        verbose_name_plural = 'Présences'
        ordering = ['enrollment__student__last_name']
        indexes = [
            models.Index(fields=['attendance_sheet', 'status']),
        ]
    
    def __str__(self):
        return f"{self.enrollment.student} - {self.attendance_sheet} - {self.get_status_display()}"
    
    @property
    def student(self):
        """Raccourci pour accéder à l'étudiant"""
        return self.enrollment.student
    
    @property
    def workshop(self):
        """Raccourci pour accéder à l'atelier"""
        return self.attendance_sheet.workshop
    
    @property
    def date(self):
        """Raccourci pour accéder à la date"""
        return self.attendance_sheet.date

class Donation(models.Model):
    """Modèle pour les dons (supports both authenticated and anonymous donors)"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('completed', 'Complété'),
        ('failed', 'Échoué'),
        ('cancelled', 'Annulé'),
    ]
    
    DONATION_TYPE_CHOICES = [
        ('one_time', 'Don unique'),
        ('monthly', 'Mensuel'),
        ('annual', 'Annuel'),
    ]
    
    # For authenticated donors
    donor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='donations', 
                             verbose_name='Donateur', null=True, blank=True)
    
    # For anonymous donors
    donor_name = models.CharField(max_length=200, blank=True, verbose_name='Nom du donateur')
    donor_email = models.EmailField(blank=True, verbose_name='Email du donateur')
    
    # Donation details
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Montant')
    donation_type = models.CharField(max_length=20, choices=DONATION_TYPE_CHOICES, default='one_time', verbose_name='Type de don')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Statut')
    donation_date = models.DateTimeField(auto_now_add=True, verbose_name='Date du don')
    payment_date = models.DateTimeField(null=True, blank=True, verbose_name='Date de paiement')
    message = models.TextField(blank=True, verbose_name='Message')
    notes = models.TextField(blank=True, verbose_name='Notes')
    
    # Payment information
    payment_method = models.CharField(max_length=50, blank=True, verbose_name='Méthode de paiement')
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name='ID de transaction (Checkout Intent)')
    helloasso_order_id = models.CharField(max_length=100, blank=True, verbose_name='ID de commande HelloAsso')
    helloasso_payment_id = models.CharField(max_length=100, blank=True, verbose_name='ID de paiement HelloAsso')
    receipt_url = models.URLField(blank=True, verbose_name='URL du reçu')
    tax_receipt_url = models.URLField(blank=True, verbose_name='URL du reçu fiscal')
    
    class Meta:
        verbose_name = 'Don'
        verbose_name_plural = 'Dons'
        ordering = ['-donation_date']
    
    def __str__(self):
        if self.donor:
            return f"Don de {self.donor.get_full_name() or self.donor.username} - {self.amount}€"
        elif self.donor_name:
            return f"Don de {self.donor_name} - {self.amount}€"
        else:
            return f"Don anonyme - {self.amount}€"
    
    def get_amount_display(self):
        """Return formatted amount"""
        return f"{self.amount}€"
    
    def is_anonymous(self):
        """Check if donation is anonymous"""
        return self.donor is None
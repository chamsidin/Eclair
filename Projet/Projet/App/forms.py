from django import forms
from django.contrib.auth.forms import UserCreationForm
from captcha.fields import CaptchaField
from .models import User, ParentApplication, PartnerApplication, IntervenantApplication, Establishment, Workshop, Room, Document, Level

class ContactForm(forms.Form):
    """Formulaire de contact pour la page d'accueil"""
    SUBJECT_CHOICES = [
        ('', 'Sélectionnez un sujet'),
        ("Inscription d'un enfant", "Inscription d'un enfant"),
        ("Devenir intervenant", "Devenir intervenant"),
        ("Partenariat établissement", "Partenariat établissement"),
        ("Donation", "Donation"),
        ("Autre demande", "Autre demande"),
    ]
    
    full_name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary smooth-transition',
            'placeholder': 'Votre nom'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary smooth-transition',
            'placeholder': 'votre.email@exemple.fr'
        })
    )
    subject = forms.ChoiceField(
        choices=SUBJECT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary smooth-transition'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary smooth-transition',
            'placeholder': 'Votre message...',
            'rows': 5
        })
    )
    captcha = CaptchaField(
        label='Vérification',
        error_messages={'invalid': 'Le code de vérification est incorrect.'}
    )

class ParentInscriptionForm(forms.ModelForm):
    """Formulaire d'inscription pour les parents"""
    
    class Meta:
        model = ParentApplication
        fields = [
            'parent_first_name', 'parent_last_name', 'parent_email', 'parent_phone',
            'school_name', 'motivation', 'wants_to_donate', 'donation_amount'
        ]
        widgets = {
            'parent_first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom du parent'
            }),
            'parent_last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du parent'
            }),
            'parent_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email du parent'
            }),
            'parent_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Téléphone du parent'
            }),
            'school_name': forms.Select(attrs={
                'class': 'form-control',
            }),
            'motivation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Décrivez pourquoi vous souhaitez inscrire votre(vos) enfant(s)...'
            }),
            'wants_to_donate': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'donation_amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Montant en euros',
                'step': '0.01',
                'min': '0',
                'style': 'padding-right: 50px;'
            })
        }
        labels = {
            'parent_first_name': 'Prénom du parent',
            'parent_last_name': 'Nom du parent',
            'parent_email': 'Email du parent',
            'parent_phone': 'Téléphone du parent',
            'school_name': 'Nom de l\'établissement scolaire',
            'motivation': 'Motivation',
            'wants_to_donate': 'Souhaitez-vous faire un don ?',
            'donation_amount': 'Montant du don (€)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Change school_name to ModelChoiceField for establishments
        self.fields['school_name'] = forms.ModelChoiceField(
            queryset=Establishment.objects.all().order_by('name'),
            widget=forms.Select(attrs={
                'class': 'form-control',
            }),
            label='Établissement scolaire',
            required=False,  # Not required since each student has their own establishment
            empty_label='Sélectionnez un établissement'
        )
        for field in self.fields.values():
            if hasattr(field, 'required'):
                field.required = True
        # Make motivation, school_name, and donation fields optional
        self.fields['motivation'].required = False
        self.fields['school_name'].required = False
        self.fields['wants_to_donate'].required = False
        self.fields['donation_amount'].required = False
    
    def save(self, commit=True, students_data=None):
        instance = super().save(commit=False)
        # Extract establishment name and save it to school_name field
        establishment = self.cleaned_data.get('school_name')
        if establishment:
            instance.school_name = establishment.name
        
        # Save students data if provided
        if students_data:
            instance.students = students_data
        
        if commit:
            instance.save()
        return instance

class ProviseurInscriptionForm(forms.ModelForm):
    """Formulaire d'inscription pour les proviseurs/directeurs d'établissement"""
    
    class Meta:
        model = PartnerApplication
        fields = [
            'school_name', 'contact_name', 'contact_email', 'contact_phone',
            'school_address', 'motivation'
        ]
        widgets = {
            'school_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'établissement'
            }),
            'contact_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom du proviseur/directeur'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email de contact'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Téléphone de contact'
            }),
            'school_address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse complète de l\'établissement'
            }),
            'motivation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Décrivez pourquoi vous souhaitez devenir partenaire...'
            })
        }
        labels = {
            'school_name': 'Nom de l\'établissement',
            'contact_name': 'Nom du proviseur/directeur',
            'contact_email': 'Email de contact',
            'contact_phone': 'Téléphone de contact',
            'school_address': 'Adresse de l\'établissement',
            'motivation': 'Motivation'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True

class IntervenantInscriptionForm(forms.ModelForm):
    """Formulaire de candidature pour devenir intervenant"""
    
    class Meta:
        model = IntervenantApplication
        fields = [
            'prenom', 'nom', 'email', 'telephone', 'date_naissance', 'adresse',
            'niveau_etudes', 'domaine_etudes', 'experience', 'matieres',
            'disponibilites', 'heures_semaine', 'motivation',
            'cv', 'autre_documents'
        ]
        widgets = {
            'prenom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre prénom'
            }),
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre nom'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre email'
            }),
            'telephone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre téléphone'
            }),
            'date_naissance': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'adresse': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Adresse complète'
            }),
            'niveau_etudes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Bac+3, Master, Licence...'
            }),
            'domaine_etudes': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Mathématiques, Lettres, Sciences...'
            }),
            'experience': forms.Select(attrs={
                'class': 'form-control'
            }),
            'matieres': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Listez les matières (séparez par des virgules)'
            }),
            'disponibilites': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Indiquez vos créneaux disponibles (jours et horaires)'
            }),
            'heures_semaine': forms.Select(attrs={
                'class': 'form-control'
            }),
            'motivation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Parlez-nous de vos motivations...'
            }),
            'cv': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            }),
            'autre_documents': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Définir les choix pour experience
        self.fields['experience'] = forms.ChoiceField(
            choices=[
                ('', '-- Sélectionner --'),
                ('Aucune', 'Aucune expérience'),
                ('Moins de 1 an', 'Moins de 1 an'),
                ('1-2 ans', '1 à 2 ans'),
                ('2-5 ans', '2 à 5 ans'),
                ('Plus de 5 ans', 'Plus de 5 ans'),
            ],
            widget=forms.Select(attrs={'class': 'form-control'}),
            required=False
        )
        
        # Définir les choix pour heures_semaine
        self.fields['heures_semaine'] = forms.ChoiceField(
            choices=[
                ('', '-- Sélectionner --'),
                ('1-5', '1 à 5 heures'),
                ('5-10', '5 à 10 heures'),
                ('10-15', '10 à 15 heures'),
                ('15-20', '15 à 20 heures'),
                ('Plus de 20', 'Plus de 20 heures'),
            ],
            widget=forms.Select(attrs={'class': 'form-control'}),
            required=True
        )
        
        # Rendre les champs obligatoires sauf ceux spécifiquement optionnels
        for field_name, field in self.fields.items():
            if field_name not in ['experience', 'autre_documents']:
                field.required = True
        
        # CV est obligatoire
        self.fields['cv'].required = True
        # Autre documents est optionnel
        self.fields['autre_documents'].required = False

class UserRegistrationForm(UserCreationForm):
    """Formulaire d'inscription utilisateur étendu"""
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=20, required=False)
    role = forms.ChoiceField(choices=User.ROLE_CHOICES, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'role', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if hasattr(field, 'widget') and hasattr(field.widget, 'attrs'):
                field.widget.attrs.update({'class': 'form-control'})

class UserProfileForm(forms.ModelForm):
    """Formulaire de mise à jour du profil utilisateur"""
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom d\'utilisateur'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Téléphone'
            }),
        }
        labels = {
            'username': 'Nom d\'utilisateur',
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'phone': 'Téléphone',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make username required
        self.fields['username'].required = True
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Check if username is already taken by another user
            user_with_username = User.objects.filter(username=username).exclude(pk=self.instance.pk)
            if user_with_username.exists():
                raise forms.ValidationError('Ce nom d\'utilisateur est déjà utilisé. Veuillez en choisir un autre.')
        return username

class AdminUserCreationForm(forms.ModelForm):
    """Formulaire pour la création d'utilisateurs par l'admin (sans mot de passe)"""
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'role')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'username': 'Nom d\'utilisateur',
            'email': 'Email',
            'first_name': 'Prénom',
            'last_name': 'Nom',
            'phone': 'Téléphone',
            'role': 'Rôle',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields required
        self.fields['username'].required = True
        self.fields['email'].required = True
        self.fields['role'].required = True

class EstablishmentForm(forms.ModelForm):
    """Formulaire de création d'établissement"""
    
    class Meta:
        model = Establishment
        fields = [
            'name', 'address', 'city', 'postal_code', 'region', 
            'school_type', 'contact_email', 'contact_phone', 'is_partner', 'partnership_date'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nom de l\'établissement'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Adresse complète'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ville'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Code postal'
            }),
            'region': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Région'
            }),
            'school_type': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Lycée, Collège, etc.'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email de contact'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Téléphone de contact'
            }),
            'is_partner': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'partnership_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'name': 'Nom',
            'address': 'Adresse',
            'city': 'Ville',
            'postal_code': 'Code postal',
            'region': 'Région',
            'school_type': 'Type d\'établissement',
            'contact_email': 'Email de contact',
            'contact_phone': 'Téléphone de contact',
            'is_partner': 'Partenaire',
            'partnership_date': 'Date de partenariat',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make required fields
        required_fields = ['name', 'address', 'city', 'postal_code', 'school_type', 'contact_email', 'contact_phone']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

class WorkshopForm(forms.ModelForm):
    """Formulaire de création d'atelier"""
    
    class Meta:
        model = Workshop
        fields = [
            'title', 'description', 'establishment', 'intervenant', 'room', 'level',
            'day', 'max_students', 'start_date', 'end_date', 'is_recurrent', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre de l\'atelier'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Description de l\'atelier'
            }),
            'establishment': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_establishment'
            }),
            'intervenant': forms.Select(attrs={
                'class': 'form-control',
            }),
            'room': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_room'
            }),
            'level': forms.Select(attrs={
                'class': 'form-control',
            }),
            'day': forms.Select(attrs={
                'class': 'form-control',
            }),
            'max_students': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Nombre maximum d\'élèves'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_recurrent': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            })
        }
        labels = {
            'title': 'Titre',
            'description': 'Description',
            'establishment': 'Établissement',
            'intervenant': 'Intervenant',
            'room': 'Salle',
            'level': 'Niveau',
            'day': 'Jour de la semaine',
            'max_students': 'Nombre maximum d\'élèves',
            'start_date': 'Date de début',
            'end_date': 'Date de fin',
            'is_recurrent': 'Atelier récurrent (répété chaque semaine)',
            'is_active': 'Actif'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter intervenants to only those with role='intervenant'
        self.fields['intervenant'].queryset = User.objects.filter(role='intervenant').order_by('first_name', 'last_name', 'username')
        self.fields['establishment'].queryset = Establishment.objects.all().order_by('name')
        self.fields['establishment'].empty_label = 'Sélectionnez un établissement'
        
        # Format datetime fields for edit mode (datetime-local input format)
        if self.instance and self.instance.pk:
            if self.instance.start_date:
                self.initial['start_date'] = self.instance.start_date.strftime('%Y-%m-%dT%H:%M')
            if self.instance.end_date:
                self.initial['end_date'] = self.instance.end_date.strftime('%Y-%m-%dT%H:%M')
        
        # Rooms - filter by establishment if one is selected in initial data or POST data
        establishment_id = None
        if self.data and 'establishment' in self.data:
            try:
                establishment_id = int(self.data['establishment'])
            except (ValueError, TypeError):
                pass
        elif self.instance and self.instance.pk:
            # In edit mode, use the instance's establishment
            establishment_id = self.instance.establishment_id
        elif self.initial and 'establishment' in self.initial:
            establishment_id = self.initial['establishment'].id if hasattr(self.initial['establishment'], 'id') else None
        
        if establishment_id:
            self.fields['room'].queryset = Room.objects.filter(establishment_id=establishment_id, is_available=True).order_by('name')
        else:
            # Start with empty queryset, will be populated via JavaScript
            self.fields['room'].queryset = Room.objects.none()
        
        self.fields['room'].required = False
        self.fields['room'].empty_label = 'Sélectionnez une salle (optionnel)'
        
        # Levels
        self.fields['level'].queryset = Level.objects.all().order_by('order', 'name')
        self.fields['level'].required = True
        self.fields['level'].empty_label = 'Sélectionnez un niveau'
        
        # Make required fields
        required_fields = ['title', 'description', 'establishment', 'intervenant', 'max_students', 'start_date', 'end_date']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        establishment = cleaned_data.get('establishment')
        room = cleaned_data.get('room')
        
        # Validate that room belongs to the selected establishment
        if room and establishment:
            if room.establishment != establishment:
                raise forms.ValidationError({
                    'room': 'La salle sélectionnée n\'appartient pas à l\'établissement choisi.'
                })
        
        # Validate that end_date is after start_date
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        if start_date and end_date and end_date <= start_date:
            raise forms.ValidationError({
                'end_date': 'La date de fin doit être postérieure à la date de début.'
            })
        
        return cleaned_data

class DocumentForm(forms.ModelForm):
    """Formulaire pour l'upload de documents par les intervenants"""
    
    class Meta:
        model = Document
        fields = ['title', 'description', 'file', 'document_type', 'workshops']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Titre du document'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description du document (optionnel)'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            }),
            'document_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'workshops': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 5,
            }),
        }
        labels = {
            'title': 'Titre',
            'description': 'Description',
            'file': 'Fichier',
            'document_type': 'Type de document',
            'workshops': 'Ateliers (sélectionnez un ou plusieurs)',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter workshops to only those where the user is the intervenant
        if user:
            self.fields['workshops'].queryset = Workshop.objects.filter(
                intervenant=user,
                is_active=True
            ).order_by('-start_date', 'title')
        
        # Make required fields
        required_fields = ['title', 'file', 'document_type', 'workshops']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True

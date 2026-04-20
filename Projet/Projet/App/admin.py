from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import User, Establishment, Room, Student, Level, Workshop, Enrollment, ParentApplication, PartnerApplication, IntervenantApplication, Document, Donation, Attendance, AttendanceSheet

# Register your models here.

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Administration personnalisée pour le modèle User"""
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'establishment', 'is_validated', 'is_active', 'created_at')
    list_filter = ('role', 'establishment', 'is_validated', 'is_active', 'is_staff', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {'fields': ('role', 'phone', 'establishment', 'is_validated')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {'fields': ('role', 'phone', 'establishment', 'is_validated')}),
    )

@admin.register(Establishment)
class EstablishmentAdmin(admin.ModelAdmin):
    """Administration pour le modèle Établissement"""
    list_display = ('name', 'city', 'region', 'school_type', 'is_partner', 'partnership_date', 'created_at')
    list_filter = ('is_partner', 'school_type', 'region', 'created_at')
    search_fields = ('name', 'city', 'contact_email')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'school_type', 'is_partner', 'partnership_date')
        }),
        ('Informations de contact', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Adresse', {
            'fields': ('address', 'city', 'postal_code', 'region')
        }),
    )

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    """Administration pour le modèle Salle"""
    list_display = ('name', 'establishment', 'capacity', 'is_available', 'created_at')
    list_filter = ('is_available', 'establishment', 'created_at')
    search_fields = ('name', 'establishment__name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations de la salle', {
            'fields': ('name', 'establishment', 'capacity', 'description', 'is_available')
        }),
    )

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    """Administration pour le modèle Étudiant"""
    list_display = ('first_name', 'last_name', 'email', 'parent', 'establishment', 'professor', 'classe', 'birth_date', 'created_at')
    list_filter = ('establishment', 'created_at')
    search_fields = ('first_name', 'last_name', 'email', 'parent__username', 'professor', 'classe')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations de l\'étudiant', {
            'fields': ('first_name', 'last_name', 'birth_date', 'email', 'phone')
        }),
        ('Relations', {
            'fields': ('parent', 'establishment', 'professor', 'classe')
        }),
    )

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    """Administration pour le modèle Niveau"""
    list_display = ('name', 'order', 'created_at')
    search_fields = ('name',)
    ordering = ('order',)
    
    fieldsets = (
        ('Informations du niveau', {
            'fields': ('name', 'order')
        }),
    )

@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    """Administration pour le modèle Atelier"""
    list_display = ('title', 'establishment', 'intervenant', 'level', 'day', 'room', 'max_students', 'start_date', 'end_date', 'is_recurrent', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_recurrent', 'day', 'establishment', 'level', 'intervenant__role', 'start_date', 'created_at')
    search_fields = ('title', 'description', 'establishment__name', 'intervenant__username', 'room__name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations de l\'atelier', {
            'fields': ('title', 'description', 'level', 'max_students', 'is_active')
        }),
        ('Planning', {
            'fields': ('day', 'start_date', 'end_date', 'is_recurrent', 'room')
        }),
        ('Relations', {
            'fields': ('establishment', 'intervenant')
        }),
    )

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """Administration pour le modèle Inscription"""
    list_display = ('student', 'workshop', 'enrollment_date', 'is_confirmed')
    list_filter = ('is_confirmed', 'enrollment_date', 'workshop__establishment')
    search_fields = ('student__first_name', 'student__last_name', 'workshop__title')
    ordering = ('-enrollment_date',)
    
    fieldsets = (
        ('Informations d\'inscription', {
            'fields': ('student', 'workshop', 'is_confirmed')
        }),
    )

@admin.register(ParentApplication)
class ParentApplicationAdmin(admin.ModelAdmin):
    """Administration pour le modèle Demande Parent"""
    list_display = ('parent_first_name', 'parent_last_name', 'students_summary', 'wants_to_donate', 'donation_display', 'status', 'created_at')
    list_filter = ('status', 'wants_to_donate', 'created_at')
    search_fields = ('parent_first_name', 'parent_last_name', 'school_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations du parent', {
            'fields': ('parent_first_name', 'parent_last_name', 'parent_email', 'parent_phone')
        }),
        ('Informations des élèves', {
            'fields': ('students_display',)
        }),
        ('Détails de la demande', {
            'fields': ('motivation', 'status', 'processed_at')
        }),
        ('Don (à l\'avenir)', {
            'fields': ('wants_to_donate', 'donation_amount'),
            'classes': ('collapse',)  # Makes this section collapsible
        }),
    )
    
    readonly_fields = ('created_at', 'students_display')
    
    def students_summary(self, obj):
        """Display summary of students in list view"""
        students = obj.get_students()
        if students:
            if len(students) == 1:
                return f"{students[0]['first_name']} {students[0]['last_name']}"
            else:
                return f"{len(students)} élève(s)"
        return "Aucun élève"
    students_summary.short_description = "Élève(s)"
    
    def students_display(self, obj):
        """Display detailed students information in detail view"""
        from django.utils.html import format_html
        students = obj.get_students()
        if not students:
            return "Aucun élève enregistré"
        
        html = '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f0f0f0;"><th style="padding:8px; border:1px solid #ddd;">Prénom</th><th style="padding:8px; border:1px solid #ddd;">Nom</th><th style="padding:8px; border:1px solid #ddd;">Date de naissance</th><th style="padding:8px; border:1px solid #ddd;">Établissement</th></tr>'
        
        for student in students:
            html += f'<tr><td style="padding:8px; border:1px solid #ddd;">{student["first_name"]}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{student["last_name"]}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{student["birth_date"]}</td>'
            html += f'<td style="padding:8px; border:1px solid #ddd;">{student.get("establishment_name", obj.school_name)}</td></tr>'
        
        html += '</table>'
        return format_html(html)
    students_display.short_description = "Élèves inscrits"
    
    def donation_display(self, obj):
        """Display donation amount in list view"""
        if obj.wants_to_donate:
            if obj.donation_amount:
                return f"{obj.donation_amount} €"
            return "Oui (montant non spécifié)"
        return "Non"
    donation_display.short_description = "Don"

@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    """Administration pour le modèle Demande Partenariat"""
    list_display = ('school_name', 'contact_name', 'contact_email', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('school_name', 'contact_name', 'contact_email')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations de l\'établissement', {
            'fields': ('school_name', 'school_address')
        }),
        ('Informations de contact', {
            'fields': ('contact_name', 'contact_email', 'contact_phone')
        }),
        ('Détails de la demande', {
            'fields': ('motivation', 'status', 'processed_at')
        }),
    )
    
    readonly_fields = ('created_at',)

@admin.register(IntervenantApplication)
class IntervenantApplicationAdmin(admin.ModelAdmin):
    """Administration pour le modèle Candidature Intervenant"""
    list_display = ('prenom', 'nom', 'email', 'telephone', 'niveau_etudes', 'status', 'created_at')
    list_filter = ('status', 'niveau_etudes', 'created_at')
    search_fields = ('prenom', 'nom', 'email', 'domaine_etudes', 'matieres')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('prenom', 'nom', 'email', 'telephone', 'date_naissance', 'adresse')
        }),
        ('Formation et expérience', {
            'fields': ('niveau_etudes', 'domaine_etudes', 'experience', 'matieres')
        }),
        ('Disponibilités', {
            'fields': ('disponibilites', 'heures_semaine')
        }),
        ('Motivation et documents', {
            'fields': ('motivation', 'cv', 'autre_documents')
        }),
        ('Statut de la candidature', {
            'fields': ('status', 'processed_at')
        }),
    )
    
    readonly_fields = ('created_at',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Administration pour le modèle Document"""
    list_display = ('title', 'uploader', 'document_type', 'file_size', 'uploaded_at', 'get_workshops_count')
    list_filter = ('document_type', 'uploaded_at', 'uploader')
    search_fields = ('title', 'description', 'uploader__username', 'uploader__first_name', 'uploader__last_name')
    ordering = ('-uploaded_at',)
    filter_horizontal = ('workshops',)  # Better widget for many-to-many
    
    fieldsets = (
        ('Informations du document', {
            'fields': ('title', 'description', 'document_type', 'file')
        }),
        ('Partage', {
            'fields': ('workshops',)
        }),
        ('Métadonnées', {
            'fields': ('uploader', 'file_size', 'uploaded_at', 'updated_at')
        }),
    )
    
    readonly_fields = ('uploaded_at', 'updated_at', 'file_size')
    
    def get_workshops_count(self, obj):
        """Return the number of workshops this document is shared with"""
        return obj.workshops.count()
    get_workshops_count.short_description = 'Ateliers'

@admin.register(AttendanceSheet)
class AttendanceSheetAdmin(admin.ModelAdmin):
    """Administration pour les feuilles de présence"""
    list_display = ('workshop', 'date', 'get_attendance_count', 'created_by', 'is_finalized', 'created_at')
    list_filter = ('is_finalized', 'date', 'workshop__establishment', 'created_at')
    search_fields = ('workshop__title', 'notes')
    ordering = ('-date',)
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('workshop', 'date', 'is_finalized')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Métadonnées', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_attendance_count(self, obj):
        """Return the number of attendance records"""
        return obj.attendances.count()
    get_attendance_count.short_description = 'Nombre de présences'

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    """Administration pour le modèle Présence"""
    list_display = ('get_student_name', 'get_workshop_title', 'get_date', 'status', 'marked_at')
    list_filter = ('status', 'attendance_sheet__date', 'attendance_sheet__workshop__establishment', 'marked_at')
    search_fields = (
        'enrollment__student__first_name', 
        'enrollment__student__last_name', 
        'attendance_sheet__workshop__title',
        'notes'
    )
    ordering = ('-attendance_sheet__date', 'enrollment__student__last_name')
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('attendance_sheet', 'enrollment', 'status')
        }),
        ('Détails', {
            'fields': ('notes',)
        }),
        ('Métadonnées', {
            'fields': ('marked_at',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('marked_at',)
    
    def get_student_name(self, obj):
        """Return the student's full name"""
        return f"{obj.enrollment.student.first_name} {obj.enrollment.student.last_name}"
    get_student_name.short_description = 'Étudiant'
    get_student_name.admin_order_field = 'enrollment__student__last_name'
    
    def get_workshop_title(self, obj):
        """Return the workshop title"""
        return obj.attendance_sheet.workshop.title
    get_workshop_title.short_description = 'Atelier'
    get_workshop_title.admin_order_field = 'attendance_sheet__workshop__title'
    
    def get_date(self, obj):
        """Return the date"""
        return obj.attendance_sheet.date
    get_date.short_description = 'Date'
    get_date.admin_order_field = 'attendance_sheet__date'
    
    # Add action to mark multiple attendances at once
    actions = ['mark_as_present', 'mark_as_absent']
    
    def mark_as_present(self, request, queryset):
        """Action pour marquer comme présent"""
        updated = queryset.update(status='present')
        self.message_user(request, f'{updated} présence(s) marquée(s) comme présent.')
    mark_as_present.short_description = 'Marquer comme présent'
    
    def mark_as_absent(self, request, queryset):
        """Action pour marquer comme absent"""
        updated = queryset.update(status='absent')
        self.message_user(request, f'{updated} présence(s) marquée(s) comme absent.')
    mark_as_absent.short_description = 'Marquer comme absent'

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    """Administration pour le modèle Don"""
    list_display = ('get_donor_display', 'amount', 'donation_type', 'status', 'donation_date', 'payment_method', 'transaction_id')
    list_filter = ('status', 'donation_type', 'donation_date', 'payment_method')
    search_fields = ('donor__username', 'donor__first_name', 'donor__last_name', 'donor_name', 'donor_email', 'transaction_id', 'helloasso_order_id', 'notes')
    ordering = ('-donation_date',)
    
    fieldsets = (
        ('Informations du donateur', {
            'fields': ('donor', 'donor_name', 'donor_email')
        }),
        ('Détails du don', {
            'fields': ('amount', 'donation_type', 'status', 'donation_date', 'payment_date', 'message')
        }),
        ('Informations de paiement HelloAsso', {
            'fields': ('payment_method', 'transaction_id', 'helloasso_order_id', 'helloasso_payment_id', 'receipt_url', 'tax_receipt_url')
        }),
        ('Notes internes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('donation_date',)
    
    def get_donor_display(self, obj):
        """Display donor name - either user or guest name"""
        if obj.donor:
            return f"{obj.donor.get_full_name() or obj.donor.username} (User)"
        elif obj.donor_name:
            return f"{obj.donor_name} (Guest)"
        else:
            return "Anonyme"
    get_donor_display.short_description = 'Donateur'

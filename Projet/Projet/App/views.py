from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.utils.crypto import get_random_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Count, Q
from django.http import JsonResponse, FileResponse
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import mimetypes
from .forms import (
    ParentInscriptionForm, ProviseurInscriptionForm, IntervenantInscriptionForm, 
    WorkshopForm, DocumentForm, UserRegistrationForm, AdminUserCreationForm, 
    EstablishmentForm, ContactForm
)
from .models import (
    User, Student, Workshop, Enrollment, ParentApplication, 
    PartnerApplication, IntervenantApplication, Establishment, Room, Document, Donation, Attendance, AttendanceSheet
)

# Create your views here.


def home(request):
    """Home page view"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Get form data
            full_name = form.cleaned_data['full_name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            
            try:
                # Get email settings from Django settings
                admin_email = settings.CONTACT_RECIPIENT_EMAIL
                from_email = settings.DEFAULT_FROM_EMAIL
                
                # Debug: Check if email settings are configured
                if not from_email or not admin_email:
                    raise ValueError(f"Email settings not configured. FROM: {from_email}, TO: {admin_email}")
                
                # Send email to admin
                admin_html = render_to_string('Mails/contact_admin_notification.html', {
                    'full_name': full_name,
                    'email': email,
                    'subject': subject,
                    'message': message,
                })
                
                admin_email_msg = EmailMultiAlternatives(
                    subject=f'Nouveau message de contact - {subject}',
                    body=f'Nom: {full_name}\nEmail: {email}\nSujet: {subject}\n\nMessage:\n{message}',
                    from_email=from_email,
                    to=[admin_email],
                    reply_to=[email],  # This makes "Reply" go to the user, not to yourself
                )
                admin_email_msg.attach_alternative(admin_html, 'text/html')
                admin_email_msg.send()
                
                # Send confirmation email to user
                user_html = render_to_string('Mails/contact_user_confirmation.html', {
                    'full_name': full_name,
                    'email': email,
                    'subject': subject,
                })
                
                user_email_msg = EmailMultiAlternatives(
                    subject='Votre message a bien été reçu - Les Éclaireurs',
                    body=f'Bonjour {full_name},\n\nVotre message concernant "{subject}" a bien été reçu. Nous vous répondrons dans les plus brefs délais.\n\nCordialement,\nL\'équipe des Éclaireurs',
                    from_email=from_email,
                    to=[email],
                )
                user_email_msg.attach_alternative(user_html, 'text/html')
                user_email_msg.send()
                
                messages.success(request, 'Votre message a été envoyé avec succès ! Vous recevrez une confirmation par email.')
                return redirect('App:home')
                
            except Exception as e:
                messages.error(request, 'Une erreur est survenue lors de l\'envoi de votre message. Veuillez réessayer plus tard.')
                import traceback
                print(f"Error sending contact email: {e}")
                print(f"Traceback: {traceback.format_exc()}")
        else:
            messages.error(request, 'Veuillez corriger les erreurs dans le formulaire.')
    else:
        form = ContactForm()
    
    context = {
        'page_title': 'Accueil - Les Éclaireurs',
        'page_description': 'Association d\'accompagnement scolaire dédiée à l\'épanouissement et la réussite des élèves.',
        'contact_form': form,
    }
    return render(request, 'Home/home.html', context)

def main_formulaires(request):
    """Page principale des formulaires d'inscription"""
    context = {
        'page_title': 'Inscriptions - Les Éclaireurs',
        'page_description': 'Choisissez le type d\'inscription qui correspond à votre situation.',
    }
    return render(request, 'Formulaires/main_formulaires.html', context)

def parent_inscription(request):
    """Vue pour l'inscription des parents"""
    if request.method == 'POST':
        form = ParentInscriptionForm(request.POST)
        
        # Debug: Print form errors if any
        if not form.is_valid():
            print("Form is not valid. Errors:", form.errors)
        
        if form.is_valid():
            # Extract students data from POST
            students_data = []
            student_index = 0
            
            # Debug: Print POST data
            print("POST data keys:", list(request.POST.keys()))
            
            while f'student_first_name_{student_index}' in request.POST:
                first_name = request.POST.get(f'student_first_name_{student_index}', '').strip()
                last_name = request.POST.get(f'student_last_name_{student_index}', '').strip()
                birth_date = request.POST.get(f'student_birth_date_{student_index}', '2010-01-01').strip()
                establishment_id = request.POST.get(f'student_establishment_{student_index}', '').strip()
                
                # Use default birth_date if not provided
                if not birth_date:
                    birth_date = '2010-01-01'
                
                print(f"Student {student_index}: {first_name} {last_name}, birth_date={birth_date}, establishment_id={establishment_id}")
                
                if first_name and last_name and establishment_id:
                    # Get establishment name
                    try:
                        establishment = Establishment.objects.get(id=establishment_id)
                        establishment_name = establishment.name
                    except Establishment.DoesNotExist:
                        establishment_name = ''
                    
                    students_data.append({
                        'first_name': first_name,
                        'last_name': last_name,
                        'birth_date': birth_date,
                        'establishment_id': establishment_id,
                        'establishment_name': establishment_name
                    })
                student_index += 1
            
            # Validate that at least one student is provided
            if not students_data:
                form.add_error(None, "Vous devez ajouter au moins un élève.")
                establishments = Establishment.objects.all().order_by('name')
                return render(request, 'Formulaires/parent_inscription.html', {
                    'form': form,
                    'establishments': establishments,
                    'page_title': 'Inscription Parent - Les Éclaireurs',
                    'page_description': 'Inscrivez votre enfant à notre programme d\'accompagnement scolaire.',
                })
            
            # Use the first student's establishment for the application school_name
            # (for backward compatibility and email purposes)
            first_establishment = students_data[0]['establishment_name']
            
            # Vérifier si un utilisateur avec cet email existe déjà
            parent_email = form.cleaned_data.get('parent_email')
            if User.objects.filter(email=parent_email).exists():
                messages.warning(request, f'Un compte avec l\'email {parent_email} existe déjà. Veuillez vous connecter ou utiliser un autre email.')
                establishments = Establishment.objects.all().order_by('name')
                return render(request, 'Formulaires/parent_inscription.html', {
                    'form': form,
                    'establishments': establishments,
                    'page_title': 'Inscription Parent - Les Éclaireurs',
                    'page_description': 'Inscrivez votre enfant à notre programme d\'accompagnement scolaire.',
                })
            
            # Sauvegarder la demande
            application = form.save(commit=False, students_data=students_data)
            application.school_name = first_establishment
            application.save()
            
            try:
                # Get email settings from Django settings
                admin_email = settings.CONTACT_RECIPIENT_EMAIL
                from_email = settings.DEFAULT_FROM_EMAIL
                
                # Debug: Check if email settings are configured
                if not from_email or not admin_email:
                    raise ValueError(f"Email settings not configured. FROM: {from_email}, TO: {admin_email}")
                
                # Send email to admin
                students_list = application.get_students()
                admin_html = render_to_string('Mails/parent_admin_notification.html', {
                    'parent_first_name': application.parent_first_name,
                    'parent_last_name': application.parent_last_name,
                    'parent_email': application.parent_email,
                    'parent_phone': application.parent_phone,
                    'students': students_list,
                    'school_name': application.school_name,
                    'motivation': application.motivation,
                })
                
                # Build email body for plain text
                students_text = '\n'.join([f"  - {s['first_name']} {s['last_name']} (né(e) le {s['birth_date']})" for s in students_list])
                
                admin_email_msg = EmailMultiAlternatives(
                    subject=f'Nouvelle demande d\'inscription parent - {application.parent_first_name} {application.parent_last_name}',
                    body=f'Parent: {application.parent_first_name} {application.parent_last_name}\nEmail: {application.parent_email}\nTéléphone: {application.parent_phone}\n\nÉlève(s):\n{students_text}\n\nÉtablissement: {application.school_name}\n\nMotivation:\n{application.motivation}',
                    from_email=from_email,
                    to=[admin_email],
                    reply_to=[application.parent_email],  # This makes "Reply" go to the parent, not to yourself
                )
                admin_email_msg.attach_alternative(admin_html, 'text/html')
                admin_email_msg.send()
                
                # Send confirmation email to parent
                user_html = render_to_string('Mails/parent_user_confirmation.html', {
                    'parent_first_name': application.parent_first_name,
                    'parent_last_name': application.parent_last_name,
                    'students': students_list,
                    'school_name': application.school_name,
                })
                
                user_email_msg = EmailMultiAlternatives(
                    subject='Votre demande d\'inscription a bien été reçue - Les Éclaireurs',
                    body=f'Bonjour {application.parent_first_name} {application.parent_last_name},\n\nNous avons bien reçu votre demande d\'inscription pour votre enfant {application.student_first_name} {application.student_last_name}.\n\nVotre demande sera examinée par notre équipe dans les plus brefs délais.\nVous recevrez une réponse par email une fois le traitement terminé.\n\nCordialement,\nL\'équipe des Éclaireurs',
                    from_email=from_email,
                    to=[application.parent_email],
                )
                user_email_msg.attach_alternative(user_html, 'text/html')
                user_email_msg.send()
                
                messages.success(request, 'Votre demande d\'inscription a été envoyée avec succès ! Vous recevrez une confirmation par email.')
                
            except Exception as e:
                messages.error(request, 'Une erreur est survenue lors de l\'envoi de votre demande. Veuillez réessayer plus tard.')
                import traceback
                print(f"Error sending parent application email: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                # Log email settings (without password) for debugging
                print(f"Email settings - FROM: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}, TO: {getattr(settings, 'CONTACT_RECIPIENT_EMAIL', 'NOT SET')}")
                print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')}")
            
            return redirect('App:parent_inscription_success')
    else:
        form = ParentInscriptionForm()
    
    # Get establishments for the student forms
    establishments = Establishment.objects.all().order_by('name')
    
    context = {
        'form': form,
        'establishments': establishments,
        'page_title': 'Inscription Parent - Les Éclaireurs',
        'page_description': 'Inscrivez votre enfant à notre programme d\'accompagnement scolaire.',
    }
    return render(request, 'Formulaires/parent_inscription.html', context)

def parent_inscription_success(request):
    """Page de confirmation après inscription parent"""
    context = {
        'page_title': 'Inscription réussie - Les Éclaireurs',
        'page_description': 'Votre demande d\'inscription a été envoyée avec succès.',
    }
    return render(request, 'Formulaires/parent_inscription_success.html', context)

def proviseur_inscription(request):
    """Vue pour l'inscription des proviseurs/directeurs"""
    if request.method == 'POST':
        form = ProviseurInscriptionForm(request.POST)
        if form.is_valid():
            # Vérifier si un utilisateur avec cet email existe déjà
            contact_email = form.cleaned_data.get('contact_email')
            if User.objects.filter(email=contact_email).exists():
                messages.warning(request, f'Un compte avec l\'email {contact_email} existe déjà. Veuillez vous connecter ou utiliser un autre email.')
                return render(request, 'Formulaires/proviseur_inscription.html', {'form': form})
            
            # Sauvegarder la demande
            application = form.save()
            
            try:
                # Get email settings from Django settings
                admin_email = settings.CONTACT_RECIPIENT_EMAIL
                from_email = settings.DEFAULT_FROM_EMAIL
                
                # Debug: Check if email settings are configured
                if not from_email or not admin_email:
                    raise ValueError(f"Email settings not configured. FROM: {from_email}, TO: {admin_email}")
                
                # Send email to admin
                admin_html = render_to_string('Mails/proviseur_admin_notification.html', {
                    'school_name': application.school_name,
                    'contact_name': application.contact_name,
                    'contact_email': application.contact_email,
                    'contact_phone': application.contact_phone,
                    'school_address': application.school_address,
                    'motivation': application.motivation,
                })
                
                admin_email_msg = EmailMultiAlternatives(
                    subject=f'Nouvelle demande de partenariat - {application.school_name}',
                    body=f'Établissement: {application.school_name}\nContact: {application.contact_name}\nEmail: {application.contact_email}\nTéléphone: {application.contact_phone}\n\nAdresse:\n{application.school_address}\n\nMotivation:\n{application.motivation}',
                    from_email=from_email,
                    to=[admin_email],
                    reply_to=[application.contact_email],  # This makes "Reply" go to the proviseur, not to yourself
                )
                admin_email_msg.attach_alternative(admin_html, 'text/html')
                admin_email_msg.send()
                
                # Send confirmation email to proviseur
                user_html = render_to_string('Mails/proviseur_user_confirmation.html', {
                    'contact_name': application.contact_name,
                    'school_name': application.school_name,
                    'school_address': application.school_address,
                })
                
                user_email_msg = EmailMultiAlternatives(
                    subject='Votre demande de partenariat a bien été reçue - Les Éclaireurs',
                    body=f'Bonjour {application.contact_name},\n\nNous avons bien reçu votre demande de partenariat pour l\'établissement {application.school_name}.\n\nVotre demande sera examinée par notre équipe dans les plus brefs délais.\nNous vous contacterons pour discuter de vos besoins et organiser une rencontre.\n\nCordialement,\nL\'équipe des Éclaireurs',
                    from_email=from_email,
                    to=[application.contact_email],
                )
                user_email_msg.attach_alternative(user_html, 'text/html')
                user_email_msg.send()
                
                messages.success(request, 'Votre demande de partenariat a été envoyée avec succès ! Vous recevrez une confirmation par email.')
                
            except Exception as e:
                messages.error(request, 'Une erreur est survenue lors de l\'envoi de votre demande. Veuillez réessayer plus tard.')
                import traceback
                print(f"Error sending proviseur application email: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                # Log email settings (without password) for debugging
                print(f"Email settings - FROM: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}, TO: {getattr(settings, 'CONTACT_RECIPIENT_EMAIL', 'NOT SET')}")
                print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')}")
            
            return redirect('App:proviseur_inscription_success')
    else:
        form = ProviseurInscriptionForm()
    
    context = {
        'form': form,
        'page_title': 'Demande de Partenariat - Les Éclaireurs',
        'page_description': 'Devenez partenaire de notre programme d\'accompagnement scolaire.',
    }
    return render(request, 'Formulaires/proviseur_inscription.html', context)

def proviseur_inscription_success(request):
    """Page de confirmation après inscription proviseur"""
    context = {
        'page_title': 'Demande envoyée - Les Éclaireurs',
        'page_description': 'Votre demande de partenariat a été envoyée avec succès.',
    }
    return render(request, 'Formulaires/proviseur_inscription_success.html', context)

def intervenant_inscription(request):
    """Vue pour l'inscription des intervenants"""
    if request.method == 'POST':
        form = IntervenantInscriptionForm(request.POST, request.FILES)
        if form.is_valid():
            # Vérifier si un utilisateur avec cet email existe déjà
            email = form.cleaned_data.get('email')
            if User.objects.filter(email=email).exists():
                messages.warning(request, f'Un compte avec l\'email {email} existe déjà. Veuillez vous connecter ou utiliser un autre email.')
                return render(request, 'Formulaires/intervenant_inscription.html', {'form': form})
            
            # Sauvegarder la demande
            application = form.save()
            
            try:
                # Get email settings from Django settings
                admin_email = settings.CONTACT_RECIPIENT_EMAIL
                from_email = settings.DEFAULT_FROM_EMAIL
                
                # Debug: Check if email settings are configured
                if not from_email or not admin_email:
                    raise ValueError(f"Email settings not configured. FROM: {from_email}, TO: {admin_email}")
                
                # Send email to admin
                admin_html = render_to_string('Mails/intervenant_admin_notification.html', {
                    'prenom': application.prenom,
                    'nom': application.nom,
                    'email': application.email,
                    'telephone': application.telephone,
                    'date_naissance': application.date_naissance,
                    'adresse': application.adresse,
                    'niveau_etudes': application.niveau_etudes,
                    'domaine_etudes': application.domaine_etudes,
                    'experience': application.experience,
                    'matieres': application.matieres,
                    'disponibilites': application.disponibilites,
                    'heures_semaine': application.heures_semaine,
                    'motivation': application.motivation,
                })
                
                admin_email_msg = EmailMultiAlternatives(
                    subject=f'Nouvelle candidature intervenant - {application.prenom} {application.nom}',
                    body=f'Candidat: {application.prenom} {application.nom}\nEmail: {application.email}\nTéléphone: {application.telephone}\nDate de naissance: {application.date_naissance}\nAdresse: {application.adresse}\n\nFormation:\nNiveau: {application.niveau_etudes}\nDomaine: {application.domaine_etudes}\nExpérience: {application.experience or "Non spécifiée"}\nMatières: {application.matieres}\n\nDisponibilités:\n{application.disponibilites}\nHeures/semaine: {application.heures_semaine}\n\nMotivation:\n{application.motivation}',
                    from_email=from_email,
                    to=[admin_email],
                    reply_to=[application.email],  # This makes "Reply" go to the intervenant, not to yourself
                )
                admin_email_msg.attach_alternative(admin_html, 'text/html')
                admin_email_msg.send()
                
                # Send confirmation email to intervenant
                user_html = render_to_string('Mails/intervenant_user_confirmation.html', {
                    'prenom': application.prenom,
                    'nom': application.nom,
                    'niveau_etudes': application.niveau_etudes,
                    'domaine_etudes': application.domaine_etudes,
                    'matieres': application.matieres,
                    'disponibilites': application.disponibilites,
                    'heures_semaine': application.heures_semaine,
                })
                
                user_email_msg = EmailMultiAlternatives(
                    subject='Votre candidature a bien été reçue - Les Éclaireurs',
                    body=f'Bonjour {application.prenom} {application.nom},\n\nNous avons bien reçu votre candidature pour devenir intervenant au sein de notre association.\n\nVotre dossier sera examiné par notre équipe prochainement.\nSi votre profil correspond à nos besoins, nous vous contacterons pour organiser un entretien.\n\nNous vous remercions pour l\'intérêt que vous portez à notre association.\n\nCordialement,\nL\'équipe Les Éclaireurs',
                    from_email=from_email,
                    to=[application.email],
                )
                user_email_msg.attach_alternative(user_html, 'text/html')
                user_email_msg.send()
                
                messages.success(request, 'Votre candidature a été envoyée avec succès ! Vous recevrez une confirmation par email.')
                
            except Exception as e:
                messages.error(request, 'Une erreur est survenue lors de l\'envoi de votre candidature. Veuillez réessayer plus tard.')
                import traceback
                print(f"Error sending intervenant application email: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                # Log email settings (without password) for debugging
                print(f"Email settings - FROM: {getattr(settings, 'DEFAULT_FROM_EMAIL', 'NOT SET')}, TO: {getattr(settings, 'CONTACT_RECIPIENT_EMAIL', 'NOT SET')}")
                print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'NOT SET')}")
            return redirect('App:intervenant_inscription_success')
        else:
            messages.error(request, 'Veuillez corriger les erreurs dans le formulaire.')
    else:
        form = IntervenantInscriptionForm()
    
    context = {
        'form': form,
        'page_title': 'Devenir Intervenant - Les Éclaireurs',
        'page_description': 'Rejoignez notre équipe d\'intervenants et contribuez à l\'accompagnement scolaire.',
    }
    return render(request, 'Formulaires/intervenant_inscription.html', context)

def intervenant_inscription_success(request):
    """Page de confirmation après candidature intervenant"""
    context = {
        'page_title': 'Candidature envoyée - Les Éclaireurs',
        'page_description': 'Votre candidature a été envoyée avec succès.',
    }
    return render(request, 'Formulaires/intervenant_inscription_success.html', context)

# Dashboard Views

def role_required(role):
    """Decorator to check if user has the required role"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role != role:
                messages.error(request, 'Vous n\'avez pas les permissions nécessaires pour accéder à cette page.')
                return redirect('App:home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

@login_required
@role_required('admin')
def admin_dashboard(request):
    """Dashboard administrateur"""
    # Statistiques générales
    total_users = User.objects.count()
    total_students = Student.objects.count()
    total_workshops = Workshop.objects.count()
    total_establishments = Establishment.objects.count()
    
    # Demandes en attente
    pending_parent_apps = ParentApplication.objects.filter(status='pending').count()
    pending_partner_apps = PartnerApplication.objects.filter(status='pending').count()
    pending_intervenant_apps = IntervenantApplication.objects.filter(status='pending').count()
    
    # Utilisateurs non validés
    unvalidated_users = User.objects.filter(is_validated=False).count()
    
    # Statistiques par rôle
    users_by_role = User.objects.values('role').annotate(count=Count('role'))
    
    # Statistiques de dons
    from django.db.models import Sum
    completed_donations = Donation.objects.filter(status='completed')
    total_donations_amount = completed_donations.aggregate(Sum('amount'))['amount__sum'] or 0
    total_donations_count = completed_donations.count()
    
    # Dernières activités
    recent_applications = ParentApplication.objects.filter(status='pending').order_by('-created_at')[:5]
    recent_partnerships = PartnerApplication.objects.filter(status='pending').order_by('-created_at')[:5]
    recent_intervenant_apps = IntervenantApplication.objects.filter(status='pending').order_by('-created_at')[:5]
    
    # Inscriptions ateliers en attente
    pending_enrollments = Enrollment.objects.filter(is_confirmed=False).select_related('student', 'workshop').order_by('-enrollment_date')[:10]
    
    context = {
        'page_title': 'Tableau de bord Administrateur',
        'total_users': total_users,
        'total_students': total_students,
        'total_workshops': total_workshops,
        'total_establishments': total_establishments,
        'pending_parent_apps': pending_parent_apps,
        'pending_partner_apps': pending_partner_apps,
        'pending_intervenant_apps': pending_intervenant_apps,
        'unvalidated_users': unvalidated_users,
        'users_by_role': users_by_role,
        'recent_applications': recent_applications,
        'recent_partnerships': recent_partnerships,
        'recent_intervenant_apps': recent_intervenant_apps,
        'total_donations_amount': total_donations_amount,
        'total_donations_count': total_donations_count,
        'pending_enrollments': pending_enrollments.count(),
        'recent_enrollments': pending_enrollments,
    }
    return render(request, 'Dashboards/dashboard_Admin/admin_dashboard.html', context)

@login_required
@role_required('admin')
def admin_users_list(request):
    """Liste des utilisateurs pour l'admin"""
    # Handle POST request for creating user
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Set an unusable password - user will reset via email
            user.set_unusable_password()
            # Users created by admin are automatically validated
            user.is_validated = True
            user.save()
            
            # Send account creation email with password set link
            try:
                from django.contrib.sites.shortcuts import get_current_site
                from django.utils.http import urlsafe_base64_encode
                from django.utils.encoding import force_bytes
                from django.contrib.auth.tokens import default_token_generator
                
                current_site = get_current_site(request)
                protocol = 'https' if request.is_secure() else 'http'
                
                # Generate password reset token
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                
                # Render email template
                html_message = render_to_string('Mails/user_account_created_email.html', {
                    'user': user,
                    'domain': current_site.domain,
                    'protocol': protocol,
                    'uid': uid,
                    'token': token,
                })
                
                # Plain text fallback
                plain_message = f'''
Bonjour {user.first_name} {user.last_name if user.first_name else user.username},

Un compte a été créé pour vous sur la plateforme Les Éclaireurs.

Nom d'utilisateur : {user.username}
Email : {user.email}
Rôle : {user.get_role_display()}

Pour activer votre compte, définissez votre mot de passe en cliquant sur ce lien :
{protocol}://{current_site.domain}{reverse('App:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})}

Ce lien est valide pendant 7 jours.

Cordialement,
L'équipe des Éclaireurs
                '''
                
                # Send email
                email_msg = EmailMultiAlternatives(
                    subject='Votre compte Les Éclaireurs a été créé - Définissez votre mot de passe',
                    body=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[user.email],
                )
                email_msg.attach_alternative(html_message, 'text/html')
                email_msg.send()
                
                messages.success(request, f'L\'utilisateur "{user.username}" a été créé avec succès! Un email a été envoyé à {user.email}.')
            except Exception as e:
                messages.warning(request, f'L\'utilisateur "{user.username}" a été créé, mais l\'email n\'a pas pu être envoyé: {str(e)}')
            
            return redirect('App:admin_users_list')
        else:
            messages.error(request, 'Erreur lors de la création de l\'utilisateur. Veuillez corriger les erreurs.')
    else:
        form = AdminUserCreationForm()
    
    users = User.objects.all().order_by('-created_at')
    
    # Filtrage par rôle si spécifié
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Filtrage par validation
    validation_filter = request.GET.get('validated')
    if validation_filter == 'true':
        users = users.filter(is_validated=True)
    elif validation_filter == 'false':
        users = users.filter(is_validated=False)
    
    context = {
        'page_title': 'Liste des Utilisateurs',
        'users': users,
        'role_filter': role_filter,
        'validation_filter': validation_filter,
        'user_form': form,
    }
    return render(request, 'Dashboards/dashboard_Admin/admin_users_list.html', context)

@login_required
@role_required('admin')
def admin_students_list(request):
    """Liste des étudiants pour l'admin"""
    students = Student.objects.all().select_related('parent', 'establishment').order_by('-created_at')
    
    # Filtrage par établissement si spécifié
    establishment_filter = request.GET.get('establishment')
    if establishment_filter:
        students = students.filter(establishment_id=establishment_filter)
    
    establishments = Establishment.objects.all()
    
    context = {
        'page_title': 'Liste des Élèves',
        'students': students,
        'establishments': establishments,
        'establishment_filter': establishment_filter,
    }
    return render(request, 'Dashboards/dashboard_Admin/admin_students_list.html', context)

@login_required
@role_required('admin')
def admin_workshops_list(request):
    """Liste des ateliers pour l'admin"""
    workshops = Workshop.objects.all().select_related('establishment', 'intervenant', 'room').order_by('-created_at')
    
    # Handle POST request for creating workshop
    if request.method == 'POST':
        form = WorkshopForm(request.POST)
        if form.is_valid():
            workshop = form.save()
            messages.success(request, f'L\'atelier "{workshop.title}" a été créé avec succès!')
            return redirect('App:admin_workshops_list')
        else:
            messages.error(request, 'Erreur lors de la création de l\'atelier. Veuillez corriger les erreurs.')
    else:
        form = WorkshopForm()
    
    # Filtrage par établissement si spécifié
    establishment_filter = request.GET.get('establishment')
    if establishment_filter:
        workshops = workshops.filter(establishment_id=establishment_filter)
    
    # Filtrage par statut actif/inactif
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        workshops = workshops.filter(is_active=True)
    elif status_filter == 'inactive':
        workshops = workshops.filter(is_active=False)
    
    # Calculate week dates for calendar view
    # Get week offset from query parameters (default to current week)
    week_offset = int(request.GET.get('week_offset', 0))
    
    # Calculate the Monday of the target week
    today = datetime.now().date()
    current_monday = today - timedelta(days=today.weekday())
    target_monday = current_monday + timedelta(weeks=week_offset)
    
    # Calculate all days of the week
    week_days = []
    day_mapping = {
        0: 'monday',
        1: 'tuesday', 
        2: 'wednesday',
        3: 'thursday',
        4: 'friday',
        5: 'saturday'
    }
    
    for i in range(6):  # Monday to Saturday
        day_date = target_monday + timedelta(days=i)
        week_days.append({
            'date': day_date,
            'day_name': day_mapping[i],
            'workshops': []
        })
    
    # Filter workshops for the calendar view
    for workshop in workshops:
        if workshop.is_active and workshop.start_date and workshop.end_date:
            workshop_start_date = workshop.start_date.date()
            workshop_end_date = workshop.end_date.date()
            
            if workshop.is_recurrent:
                # Recurrent workshop: appears every week on the specified day until end_date
                for day_info in week_days:
                    # Check if this day matches the workshop's day and falls within the workshop period
                    if (day_info['day_name'] == workshop.day and 
                        workshop_start_date <= day_info['date'] <= workshop_end_date):
                        day_info['workshops'].append(workshop)
            else:
                # Punctual workshop: appears only on the exact start_date
                workshop_date = workshop_start_date
                # Check if workshop date falls within this week
                if target_monday <= workshop_date < target_monday + timedelta(days=7):
                    # Find the matching day in week_days
                    for day_info in week_days:
                        if day_info['date'] == workshop_date and day_info['day_name'] == workshop.day:
                            day_info['workshops'].append(workshop)
                            break
    
    establishments = Establishment.objects.all()
    
    # Calculate previous and next week dates for navigation
    prev_week_offset = week_offset - 1
    next_week_offset = week_offset + 1
    
    context = {
        'page_title': 'Liste des Ateliers',
        'workshops': workshops,
        'establishments': establishments,
        'establishment_filter': establishment_filter,
        'status_filter': status_filter,
        'workshop_form': form,
        'week_days': week_days,
        'week_start': target_monday,
        'week_end': target_monday + timedelta(days=6),
        'week_offset': week_offset,
        'prev_week_offset': prev_week_offset,
        'next_week_offset': next_week_offset,
        'is_current_week': week_offset == 0,
    }
    return render(request, 'Dashboards/dashboard_Admin/admin_workshops_list.html', context)

@login_required
@role_required('admin')
def admin_workshop_edit(request, workshop_id):
    """Edit a workshop"""
    workshop = get_object_or_404(Workshop, id=workshop_id)
    
    if request.method == 'POST':
        form = WorkshopForm(request.POST, instance=workshop)
        if form.is_valid():
            workshop = form.save()
            messages.success(request, f'L\'atelier "{workshop.title}" a été modifié avec succès!')
            return redirect('App:admin_workshops_list')
        else:
            messages.error(request, 'Erreur lors de la modification de l\'atelier. Veuillez corriger les erreurs.')
    else:
        # Form __init__ handles date formatting and room queryset
        form = WorkshopForm(instance=workshop)
    
    # Get filters to maintain them after edit
    establishment_filter = request.GET.get('establishment')
    status_filter = request.GET.get('status')
    
    # Get all data for the page
    workshops = Workshop.objects.all().select_related('establishment', 'intervenant', 'room').order_by('-created_at')
    
    # Apply filters
    if establishment_filter:
        workshops = workshops.filter(establishment_id=establishment_filter)
    if status_filter == 'active':
        workshops = workshops.filter(is_active=True)
    elif status_filter == 'inactive':
        workshops = workshops.filter(is_active=False)
    
    establishments = Establishment.objects.all()
    
    context = {
        'page_title': 'Liste des Ateliers',
        'workshops': workshops,
        'establishments': establishments,
        'establishment_filter': establishment_filter,
        'status_filter': status_filter,
        'workshop_form': form,
        'edit_mode': True,
        'workshop_to_edit': workshop,
    }
    return render(request, 'Dashboards/dashboard_Admin/admin_workshops_list.html', context)

@login_required
@role_required('admin')
def admin_workshop_delete(request, workshop_id):
    """Delete a workshop"""
    if request.method == 'POST':
        workshop = get_object_or_404(Workshop, id=workshop_id)
        workshop_title = workshop.title
        workshop.delete()
        messages.success(request, f'L\'atelier "{workshop_title}" a été supprimé avec succès!')
    return redirect('App:admin_workshops_list')

@login_required
@role_required('admin')
def get_rooms_by_establishment(request):
    """Get rooms for an establishment (AJAX endpoint)"""
    if request.method == 'GET':
        establishment_id = request.GET.get('establishment_id')
        if establishment_id:
            rooms = Room.objects.filter(establishment_id=establishment_id, is_available=True).order_by('name')
            rooms_data = [{'id': room.id, 'name': room.name} for room in rooms]
            return JsonResponse({'success': True, 'rooms': rooms_data})
        return JsonResponse({'success': False, 'error': 'establishment_id required'})
    return JsonResponse({'success': False, 'error': 'Method not allowed'})

@login_required
def get_workshop_details(request, workshop_id):
    """Get workshop details (AJAX endpoint) - returns rendered HTML"""
    try:
        workshop = get_object_or_404(Workshop, id=workshop_id)
        
        # Check permissions: parents can only see workshops their children are enrolled in or available workshops
        if request.user.role == 'parent':
            enrolled_workshop_ids = Enrollment.objects.filter(
                student__parent=request.user
            ).values_list('workshop_id', flat=True)
            
            available_workshop_ids = Workshop.objects.filter(
                is_active=True,
                end_date__gt=timezone.now()
            ).values_list('id', flat=True)
            
            if workshop.id not in enrolled_workshop_ids and workshop.id not in available_workshop_ids:
                return JsonResponse({'success': False, 'error': 'Accès non autorisé'}, status=403)
        
        # Render the workshop details template
        html = render_to_string('Dashboards/dashboard_Parent/workshop_detail_content.html', {
            'workshop': workshop
        })
        
        return JsonResponse({'success': True, 'html': html})
    except Workshop.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Atelier non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@role_required('parent')
def get_child_details(request, child_id):
    """Get child details (AJAX endpoint) - returns rendered HTML"""
    try:
        # Get the child and ensure it belongs to the current parent
        child = get_object_or_404(Student, id=child_id, parent=request.user)
        
        # Get all enrollments for this child
        enrollments = Enrollment.objects.filter(student=child).select_related('workshop').order_by('-enrollment_date')
        
        # Render the child details template
        html = render_to_string('Dashboards/dashboard_Parent/child_detail_content.html', {
            'child': child,
            'enrollments': enrollments
        })
        
        return JsonResponse({'success': True, 'html': html})
    except Student.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Enfant non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@role_required('admin')
def get_parent_application_details(request, application_id):
    """Get parent application details (AJAX endpoint) - returns rendered HTML"""
    try:
        # Get the parent application
        application = get_object_or_404(ParentApplication, id=application_id)
        
        # Render the parent application details template
        html = render_to_string('Dashboards/dashboard_Admin/parent_application_content.html', {
            'application': application
        })
        
        return JsonResponse({'success': True, 'html': html})
    except ParentApplication.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Demande non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@role_required('admin')
def get_intervenant_application_details(request, application_id):
    """Get intervenant application details (AJAX endpoint) - returns rendered HTML"""
    try:
        # Get the intervenant application
        application = get_object_or_404(IntervenantApplication, id=application_id)
        
        # Render the intervenant application details template
        html = render_to_string('Dashboards/dashboard_Admin/intervenant_application_content.html', {
            'application': application
        })
        
        return JsonResponse({'success': True, 'html': html})
    except IntervenantApplication.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Candidature non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@role_required('admin')
def get_partnership_application_details(request, application_id):
    """Get partnership application details (AJAX endpoint) - returns rendered HTML"""
    try:
        # Get the partnership application
        application = get_object_or_404(PartnerApplication, id=application_id)
        
        # Render the partnership application details template
        html = render_to_string('Dashboards/dashboard_Admin/partnership_application_content.html', {
            'application': application
        })
        
        return JsonResponse({'success': True, 'html': html})
    except PartnerApplication.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Demande de partenariat non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@role_required('admin')
def get_enrollment_details(request, enrollment_id):
    """Get enrollment details (AJAX endpoint) - returns rendered HTML"""
    try:
        # Get the enrollment with related objects
        enrollment = get_object_or_404(Enrollment.objects.select_related('student', 'workshop', 'student__parent', 'student__establishment', 'workshop__establishment', 'workshop__intervenant', 'workshop__level'), id=enrollment_id)
        
        # Render the enrollment details template
        html = render_to_string('Dashboards/dashboard_Admin/enrollment_detail_content.html', {
            'enrollment': enrollment
        })
        
        return JsonResponse({'success': True, 'html': html})
    except Enrollment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Inscription non trouvée'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@role_required('admin')
def get_workshop_enrollments(request, workshop_id):
    """Get workshop enrollments (AJAX endpoint) - returns rendered HTML"""
    try:
        # Get the workshop with related objects
        workshop = get_object_or_404(Workshop.objects.select_related('establishment', 'intervenant'), id=workshop_id)
        
        # Get all enrollments for this workshop
        enrollments = Enrollment.objects.filter(workshop=workshop).select_related(
            'student', 'student__parent', 'student__establishment'
        ).order_by('-enrollment_date')
        
        # Calculate statistics
        total_enrollments = enrollments.count()
        confirmed_enrollments = enrollments.filter(is_confirmed=True).count()
        pending_enrollments = enrollments.filter(is_confirmed=False).count()
        remaining_places = workshop.max_students - total_enrollments
        
        # Render the workshop enrollments template
        html = render_to_string('Dashboards/dashboard_Admin/workshop_enrollments_content.html', {
            'workshop': workshop,
            'enrollments': enrollments,
            'total_enrollments': total_enrollments,
            'confirmed_enrollments': confirmed_enrollments,
            'pending_enrollments': pending_enrollments,
            'remaining_places': remaining_places
        })
        
        return JsonResponse({'success': True, 'html': html})
    except Workshop.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Atelier non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@role_required('admin')
def get_user_details(request, user_id):
    """Get user details (AJAX endpoint) - returns rendered HTML"""
    try:
        # Get the user
        user = get_object_or_404(User, id=user_id)
        
        # Get children if user is a parent
        children = None
        if user.role == 'parent':
            children = Student.objects.filter(parent=user)
        
        # Render the user details template
        html = render_to_string('Dashboards/dashboard_Admin/user_detail_content.html', {
            'user': user,
            'children': children
        })
        
        return JsonResponse({'success': True, 'html': html})
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Utilisateur non trouvé'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@role_required('intervenant')
def get_intervenant_workshop_details(request, workshop_id):
    """Get workshop details for intervenant (AJAX endpoint) - returns rendered HTML"""
    try:
        # Get the workshop and ensure it belongs to the current intervenant
        workshop = get_object_or_404(Workshop, id=workshop_id, intervenant=request.user)
        
        # Get all enrollments for this workshop
        enrollments = Enrollment.objects.filter(workshop=workshop).select_related('student', 'student__establishment').order_by('-enrollment_date')
        
        # Calculate total enrolled students
        total_enrolled = enrollments.count()
        
        # Render the workshop details template for intervenant
        html = render_to_string('Dashboards/dashboard_Intervenant/workshop_details_content.html', {
            'workshop': workshop,
            'enrollments': enrollments,
            'total_enrolled': total_enrolled
        })
        
        return JsonResponse({'success': True, 'html': html})
    except Workshop.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Atelier non trouvé ou accès non autorisé'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@role_required('intervenant')
def intervenant_documents(request):
    """View and manage documents uploaded by intervenant"""
    # Get all documents (no filter)
    documents = Document.objects.all().prefetch_related('workshops', 'uploader').order_by('-uploaded_at')
    
    # Handle POST request for uploading new document
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploader = request.user
            document.save()
            form.save_m2m()  # Save many-to-many relationships (workshops)
            messages.success(request, f'Le document "{document.title}" a été uploadé avec succès!')
            return redirect('App:intervenant_documents')
        else:
            messages.error(request, 'Erreur lors de l\'upload du document. Veuillez corriger les erreurs.')
    else:
        form = DocumentForm(user=request.user)
    
    context = {
        'page_title': 'Documents',
        'documents': documents,
        'document_form': form,
    }
    return render(request, 'Dashboards/dashboard_Intervenant/documents.html', context)

@login_required
@role_required('intervenant')
def delete_document(request, document_id):
    """Delete a document (only by its uploader)"""
    if request.method == 'POST':
        try:
            document = get_object_or_404(Document, id=document_id)
            
            # Verify that the user is the uploader
            if document.uploader != request.user:
                messages.error(request, 'Vous n\'êtes pas autorisé à supprimer ce document.')
                return redirect('App:intervenant_documents')
            
            document_title = document.title
            document.file.delete()  # Delete the physical file
            document.delete()  # Delete the database record
            
            messages.success(request, f'Le document "{document_title}" a été supprimé avec succès!')
        except Exception as e:
            messages.error(request, f'Erreur lors de la suppression: {str(e)}')
    
    return redirect('App:intervenant_documents')

@login_required
@role_required('admin')
def admin_establishments_list(request):
    """Liste des établissements pour l'admin"""
    # Handle POST request for creating establishment
    if request.method == 'POST':
        form = EstablishmentForm(request.POST)
        if form.is_valid():
            establishment = form.save()
            messages.success(request, f'L\'établissement "{establishment.name}" a été créé avec succès!')
            return redirect('App:admin_establishments_list')
        else:
            messages.error(request, 'Erreur lors de la création de l\'établissement. Veuillez corriger les erreurs.')
    else:
        form = EstablishmentForm()
    
    # Add workshop count and student count annotations
    establishments = Establishment.objects.annotate(
        workshop_count=Count('workshops', distinct=True),
        student_count=Count('students', distinct=True)
    ).order_by('-created_at')
    
    # Filtrage par type si spécifié
    type_filter = request.GET.get('type')
    if type_filter:
        establishments = establishments.filter(school_type=type_filter)
    
    # Filtrage par statut partenaire
    partner_filter = request.GET.get('partner')
    if partner_filter == 'true':
        establishments = establishments.filter(is_partner=True)
    elif partner_filter == 'false':
        establishments = establishments.filter(is_partner=False)
    
    context = {
        'page_title': 'Liste des Établissements',
        'establishments': establishments,
        'type_filter': type_filter,
        'partner_filter': partner_filter,
        'establishment_form': form,
    }
    return render(request, 'Dashboards/dashboard_Admin/admin_establishments_list.html', context)

@login_required
@role_required('admin')
def admin_donations_list(request):
    """Liste des dons pour l'admin avec statistiques"""
    donations = Donation.objects.select_related('donor').order_by('-donation_date')
    
    # Filtrage par statut si spécifié
    status_filter = request.GET.get('status')
    if status_filter:
        donations = donations.filter(status=status_filter)
    
    # Filtrage par type de don
    type_filter = request.GET.get('type')
    if type_filter:
        donations = donations.filter(donation_type=type_filter)
    
    # Statistiques globales
    from django.db.models import Sum, Count
    total_amount = Donation.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    total_count = donations.filter(status='completed').count()
    pending_count = donations.filter(status='pending').count()
    
    # Statistiques par mois (12 derniers mois)
    from django.db.models.functions import TruncMonth
    monthly_stats = Donation.objects.filter(status='completed').annotate(
        month=TruncMonth('donation_date')
    ).values('month').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-month')[:12]
    
    # Top donateurs (authenticated users only)
    top_donors = Donation.objects.filter(
        status='completed',
        donor__isnull=False
    ).values('donor__username', 'donor__first_name', 'donor__last_name').annotate(
        total=Sum('amount'),
        count=Count('id')
    ).order_by('-total')[:10]
    
    context = {
        'page_title': 'Rapports des Dons',
        'donations': donations,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'total_amount': total_amount,
        'total_count': total_count,
        'pending_count': pending_count,
        'monthly_stats': monthly_stats,
        'top_donors': top_donors,
    }
    return render(request, 'Dashboards/dashboard_Admin/admin_donations_list.html', context)

@login_required
@role_required('parent')
def parent_dashboard(request):
    """Dashboard parent"""
    # Enfants du parent
    children = Student.objects.filter(parent=request.user)
    
    # Inscriptions aux ateliers
    enrollments = Enrollment.objects.filter(student__parent=request.user).select_related('workshop', 'student')
    
    # Récupérer les établissements des enfants
    children_establishments = children.values_list('establishment_id', flat=True).distinct()
    
    # Ateliers disponibles pour inscription (seulement ceux des établissements des enfants)
    available_workshops = Workshop.objects.filter(
        is_active=True,
        end_date__gt=timezone.now(),
        establishment_id__in=children_establishments
    ).exclude(
        enrollments__student__parent=request.user
    )
    
    # Notifications (exemple simple)
    notifications = []
    for enrollment in enrollments:
        if enrollment.workshop.start_date.date() == timezone.now().date():
            notifications.append(f"Atelier '{enrollment.workshop.title}' aujourd'hui pour {enrollment.student.first_name}")
    
    # Documents partagés - Get real documents from workshops the children are enrolled in
    # Get all workshop IDs that the parent's children are enrolled in
    enrolled_workshop_ids = enrollments.values_list('workshop_id', flat=True).distinct()
    
    # Get documents associated with these workshops
    shared_documents = Document.objects.filter(
        workshops__id__in=enrolled_workshop_ids
    ).select_related('uploader').prefetch_related('workshops').distinct().order_by('-uploaded_at')
    
    # Get all establishments for the add child form
    establishments = Establishment.objects.all().order_by('name')
    
    context = {
        'page_title': 'Tableau de bord Parent',
        'children': children,
        'enrollments': enrollments,
        'available_workshops': available_workshops,
        'notifications': notifications,
        'shared_documents': shared_documents,
        'establishments': establishments,
    }
    return render(request, 'Dashboards/dashboard_Parent/parent_dashboard.html', context)

@login_required
@role_required('parent')
def add_child(request):
    """Add a new child for the parent"""
    if request.method == 'POST':
        try:
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            birth_date = request.POST.get('birth_date')
            establishment_id = request.POST.get('establishment')
            
            # Validate required fields (birth_date is optional now)
            if not all([first_name, last_name, establishment_id]):
                messages.error(request, 'Tous les champs obligatoires doivent être remplis.')
                return redirect('App:parent_dashboard')
            
            # Get establishment
            establishment = get_object_or_404(Establishment, id=establishment_id)
            
            # Use parent's email and phone for the child
            email = request.user.email
            phone = request.user.phone
            
            # Use default birth_date if not provided
            if not birth_date:
                birth_date = '2010-01-01'
            
            # Create the student
            student = Student.objects.create(
                first_name=first_name,
                last_name=last_name,
                birth_date=birth_date,
                establishment=establishment,
                parent=request.user,
                email=email,
                phone=phone
            )
            
            messages.success(request, f'{first_name} {last_name} a été ajouté(e) avec succès!')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'ajout de l\'enfant: {str(e)}')
    
    return redirect('App:parent_dashboard')

@login_required
@role_required('parent')
def parent_attendance_sheets(request):
    """View attendance sheets for parent's children (read-only)"""
    # Get parent's children
    children = Student.objects.filter(parent=request.user)
    
    # Get workshops that the children are enrolled in
    workshops = Workshop.objects.filter(
        enrollments__student__in=children
    ).distinct().order_by('title')
    
    # Get all attendance sheets for these workshops
    attendance_sheets = AttendanceSheet.objects.filter(
        workshop__in=workshops
    ).select_related('workshop', 'created_by').prefetch_related(
        'attendances__enrollment__student'
    ).order_by('-date')
    
    # Filter by child if requested
    child_id = request.GET.get('child')
    selected_child = None
    if child_id:
        selected_child = get_object_or_404(Student, id=child_id, parent=request.user)
        # Filter workshops and sheets for this specific child
        workshops = workshops.filter(enrollments__student=selected_child)
        attendance_sheets = attendance_sheets.filter(
            attendances__enrollment__student=selected_child
        ).distinct()
    
    # Filter by workshop if requested
    workshop_id = request.GET.get('workshop')
    selected_workshop = None
    if workshop_id:
        selected_workshop = get_object_or_404(Workshop, id=workshop_id)
        attendance_sheets = attendance_sheets.filter(workshop=selected_workshop)
    
    # Get selected sheet if specified
    sheet_id = request.GET.get('sheet')
    selected_sheet = None
    attendance_data = []
    
    if sheet_id:
        selected_sheet = get_object_or_404(
            AttendanceSheet,
            id=sheet_id,
            workshop__in=workshops
        )
        
        # Get attendance records for parent's children only
        attendances = selected_sheet.attendances.filter(
            enrollment__student__in=children
        ).select_related('enrollment__student')
        
        # Build attendance data
        for attendance in attendances:
            attendance_data.append({
                'student': attendance.enrollment.student,
                'status': attendance.status,
                'notes': attendance.notes,
                'enrollment': attendance.enrollment
            })
    
    context = {
        'page_title': 'Feuilles de Présence',
        'children': children,
        'workshops': workshops,
        'attendance_sheets': attendance_sheets,
        'selected_child': selected_child,
        'selected_workshop': selected_workshop,
        'selected_sheet': selected_sheet,
        'attendance_data': attendance_data,
    }
    return render(request, 'Dashboards/dashboard_Parent/parent_attendance_sheets.html', context)

@login_required
@role_required('intervenant')
def intervenant_dashboard(request):
    """Dashboard intervenant/éclaireur"""
    # Ateliers de l'intervenant
    workshops = Workshop.objects.filter(intervenant=request.user, is_active=True)
    
    # Liste des élèves inscrits aux ateliers de l'intervenant
    students = Student.objects.filter(
        enrollments__workshop__intervenant=request.user
    ).distinct()
    
    # Présences (exemple simple - à développer selon vos besoins)
    attendance_data = {}
    for workshop in workshops:
        enrollments = Enrollment.objects.filter(workshop=workshop)
        attendance_data[workshop.id] = {
            'total_enrolled': enrollments.count(),
            'confirmed': enrollments.filter(is_confirmed=True).count(),
        }
    
    # Documents uploaded by this intervenant
    documents = Document.objects.filter(uploader=request.user).prefetch_related('workshops').order_by('-uploaded_at')[:5]
    
    context = {
        'page_title': 'Tableau de bord Intervenant',
        'workshops': workshops,
        'students': students,
        'attendance_data': attendance_data,
        'recent_documents': documents,
    }
    return render(request, 'Dashboards/dashboard_Intervenant/intervenant_dashboard.html', context)

@login_required
@role_required('intervenant')
def intervenant_attendance_report(request):
    """Rapport de présence pour les intervenants"""
    from datetime import timedelta, datetime
    import json
    
    # Get intervenant's workshops
    workshops = Workshop.objects.filter(intervenant=request.user, is_active=True).prefetch_related('enrollments__student')
    
    # Get selected workshop and date from query params
    selected_workshop_id = request.GET.get('workshop')
    selected_date = request.GET.get('date')
    
    # Default to today
    if selected_date:
        try:
            selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
        except ValueError:
            selected_date = timezone.now().date()
    else:
        selected_date = timezone.now().date()
    
    # Prepare attendance data
    attendance_data = []
    selected_workshop = None
    attendance_sheet = None
    valid_dates = []
    valid_dates_json = '[]'
    stats = {
        'present': 0,
        'absent': 0,
        'total': 0
    }
    
    if selected_workshop_id:
        selected_workshop = workshops.filter(id=selected_workshop_id).first()
        if selected_workshop:
            # Calculate valid session dates for this workshop
            day_mapping = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2,
                'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
            }
            
            workshop_start = selected_workshop.start_date.date()
            workshop_end = selected_workshop.end_date.date()
            workshop_weekday = day_mapping.get(selected_workshop.day, 0)
            
            # Find all dates matching the workshop's weekday within the date range
            current_date = workshop_start
            while current_date <= workshop_end:
                if current_date.weekday() == workshop_weekday:
                    valid_dates.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)
            
            valid_dates_json = json.dumps(valid_dates)
            
            # Validate selected date
            if selected_date.strftime('%Y-%m-%d') not in valid_dates and valid_dates:
                # If selected date is invalid, default to the nearest valid date
                today_str = timezone.now().date().strftime('%Y-%m-%d')
                if today_str in valid_dates:
                    selected_date = timezone.now().date()
                elif valid_dates:
                    # Use the first valid date
                    selected_date = datetime.strptime(valid_dates[0], '%Y-%m-%d').date()
            # Try to get existing attendance sheet for this workshop + date
            try:
                attendance_sheet = AttendanceSheet.objects.get(
                    workshop=selected_workshop,
                    date=selected_date
                )
                sheet_exists = True
            except AttendanceSheet.DoesNotExist:
                sheet_exists = False
            
            # Get enrollments for this workshop
            enrollments = selected_workshop.enrollments.filter(is_confirmed=True).select_related('student')
            
            for enrollment in enrollments:
                # Get attendance if sheet exists
                if sheet_exists:
                    try:
                        attendance = Attendance.objects.get(
                            attendance_sheet=attendance_sheet,
                            enrollment=enrollment
                        )
                        status = attendance.status
                        notes = attendance.notes
                    except Attendance.DoesNotExist:
                        status = 'absent'
                        notes = ''
                else:
                    status = 'absent'
                    notes = ''
                
                attendance_data.append({
                    'enrollment': enrollment,
                    'student': enrollment.student,
                    'status': status,
                    'notes': notes
                })
                
                # Update statistics
                stats[status] = stats.get(status, 0) + 1
                stats['total'] += 1
    
    context = {
        'page_title': 'Rapport de Présence',
        'workshops': workshops,
        'selected_workshop': selected_workshop,
        'selected_date': selected_date,
        'attendance_data': attendance_data,
        'attendance_sheet': attendance_sheet,
        'stats': stats,
        'valid_dates_json': valid_dates_json,
    }
    return render(request, 'Dashboards/dashboard_Intervenant/intervenant_attendance_report.html', context)

@login_required
@role_required('professeur')
def professeur_dashboard(request):
    """Dashboard professeur"""
    # Élèves inscrits dans l'établissement du professeur
    if request.user.establishment:
        # Filter students by professor's establishment
        students = Student.objects.filter(establishment=request.user.establishment)
        # Filter workshops by professor's establishment
        workshops = Workshop.objects.filter(establishment=request.user.establishment)
    else:
        # If professor has no establishment assigned, show all students
        students = Student.objects.all()
        workshops = Workshop.objects.all()
    
    # Consultation des présences
    enrollments = Enrollment.objects.filter(
        student__in=students
    ).select_related('student', 'workshop')
    
    # Get all documents shared in workshops from this establishment
    documents = Document.objects.filter(
        workshops__in=workshops
    ).distinct().prefetch_related('workshops', 'uploader').order_by('-uploaded_at')
    
    # Get recent attendance sheets for workshops from this establishment
    attendance_sheets = AttendanceSheet.objects.filter(
        workshop__in=workshops
    ).distinct().select_related('workshop', 'created_by').prefetch_related(
        'attendances__enrollment__student'
    ).order_by('-date')[:10]
    
    context = {
        'page_title': 'Tableau de bord Professeur',
        'students': students,
        'enrollments': enrollments,
        'documents': documents,
        'attendance_sheets': attendance_sheets,
    }
    return render(request, 'Dashboards/dashboard_Professeur/professeur_dashboard.html', context)

@login_required
@role_required('professeur')
def professeur_documents(request):
    """View all documents shared by intervenants (read-only for professors)"""
    # Get students from professor's establishment
    if request.user.establishment:
        students = Student.objects.filter(establishment=request.user.establishment)
        # Get workshops from professor's establishment
        workshops = Workshop.objects.filter(establishment=request.user.establishment).distinct().order_by('title')
    else:
        students = Student.objects.all()
        # Get all workshops for filtering
        workshops = Workshop.objects.filter(
            enrollments__student__in=students
        ).distinct().order_by('title')
    
    # Get all documents shared in workshops from this establishment
    documents = Document.objects.filter(
        workshops__in=workshops
    ).distinct().prefetch_related('workshops', 'uploader').order_by('-uploaded_at')
    
    # Filter by workshop if requested
    workshop_id = request.GET.get('workshop')
    if workshop_id:
        documents = documents.filter(workshops__id=workshop_id)
    
    context = {
        'page_title': 'Documents Partagés',
        'documents': documents,
        'workshops': workshops,
        'selected_workshop_id': int(workshop_id) if workshop_id else None,
    }
    return render(request, 'Dashboards/dashboard_Professeur/professeur_documents.html', context)

@login_required
@role_required('professeur')
def professeur_attendance_sheets(request):
    """View attendance sheets with student details (read-only for professors)"""
    # Get students from professor's establishment
    if request.user.establishment:
        students = Student.objects.filter(establishment=request.user.establishment)
        # Get workshops from professor's establishment
        workshops = Workshop.objects.filter(establishment=request.user.establishment).distinct().order_by('title')
    else:
        students = Student.objects.all()
        # Get all workshops for filtering
        workshops = Workshop.objects.filter(
            enrollments__student__in=students
        ).distinct().order_by('title')
    
    # Get all attendance sheets for workshops from this establishment
    attendance_sheets = AttendanceSheet.objects.filter(
        workshop__in=workshops
    ).distinct().select_related('workshop', 'created_by').prefetch_related(
        'attendances__enrollment__student'
    ).order_by('-date')
    
    # Filter by workshop if requested
    workshop_id = request.GET.get('workshop')
    selected_workshop = None
    if workshop_id:
        selected_workshop = get_object_or_404(Workshop, id=workshop_id)
        attendance_sheets = attendance_sheets.filter(workshop=selected_workshop)
    
    # Get selected sheet if specified
    sheet_id = request.GET.get('sheet')
    selected_sheet = None
    attendance_data = []
    if sheet_id:
        selected_sheet = get_object_or_404(AttendanceSheet, id=sheet_id)
        # Get all attendances for this sheet with student details
        attendances = selected_sheet.attendances.select_related(
            'enrollment__student', 'enrollment__workshop'
        ).order_by('enrollment__student__last_name', 'enrollment__student__first_name')
        
        for attendance in attendances:
            attendance_data.append({
                'student': attendance.enrollment.student,
                'enrollment': attendance.enrollment,
                'status': attendance.status,
                'notes': attendance.notes,
            })
    
    context = {
        'page_title': 'Feuilles de Présence',
        'attendance_sheets': attendance_sheets,
        'selected_sheet': selected_sheet,
        'attendance_data': attendance_data,
        'workshops': workshops,
        'selected_workshop': selected_workshop,
    }
    return render(request, 'Dashboards/dashboard_Professeur/professeur_attendance_sheets.html', context)

# Actions pour l'admin
@login_required
@role_required('admin')
def validate_user(request, user_id):
    """Valider un utilisateur"""
    user = get_object_or_404(User, id=user_id)
    user.is_validated = True
    user.save()
    messages.success(request, f'Utilisateur {user.username} validé avec succès.')
    return redirect('App:admin_dashboard')

@login_required
@role_required('admin')
def validate_parent_application(request, app_id):
    """Valider une demande parent et créer les comptes utilisateur et étudiant"""
    app = get_object_or_404(ParentApplication, id=app_id)
    
    try:
        # Créer le compte utilisateur parent
        username = f"{app.parent_first_name.lower()}.{app.parent_last_name.lower()}"
        # Vérifier si le nom d'utilisateur existe déjà
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}{counter}"
            counter += 1
        
        # Créer l'utilisateur parent avec un mot de passe temporaire (sera rendu non utilisable)
        parent_user = User.objects.create_user(
            username=username,
            email=app.parent_email,
            first_name=app.parent_first_name,
            last_name=app.parent_last_name,
            role='parent',
            phone=app.parent_phone,
            is_validated=True,
            password=get_random_string(20)  # Mot de passe temporaire (sera rendu non utilisable)
        )
        # Définir un mot de passe non utilisable pour forcer la réinitialisation
        parent_user.set_unusable_password()
        parent_user.save()
        
        # Créer tous les étudiants
        students_list = app.get_students()
        created_students = []
        for student_data in students_list:
            from datetime import datetime
            # Parse birth_date if it's a string
            birth_date = student_data['birth_date']
            if isinstance(birth_date, str):
                birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
            
            # Get or create establishment for this student
            if 'establishment_id' in student_data and student_data['establishment_id']:
                # New format with establishment_id
                try:
                    establishment = Establishment.objects.get(id=student_data['establishment_id'])
                except Establishment.DoesNotExist:
                    # Fallback to creating from school_name
                    establishment, created = Establishment.objects.get_or_create(
                        name=student_data.get('establishment_name', app.school_name),
                        defaults={
                            'address': 'À définir',
                            'city': 'À définir',
                            'postal_code': '00000',
                            'region': 'À définir',
                            'school_type': 'Lycée',
                            'contact_email': app.parent_email,
                            'contact_phone': app.parent_phone,
                            'is_partner': False,
                        }
                    )
            else:
                # Legacy format - use app.school_name
                establishment, created = Establishment.objects.get_or_create(
                    name=app.school_name,
                    defaults={
                        'address': 'À définir',
                        'city': 'À définir',
                        'postal_code': '00000',
                        'region': 'À définir',
                        'school_type': 'Lycée',
                        'contact_email': app.parent_email,
                        'contact_phone': app.parent_phone,
                        'is_partner': False,
                    }
                )
            
            student = Student.objects.create(
                first_name=student_data['first_name'],
                last_name=student_data['last_name'],
                email=app.parent_email,  # Utiliser l'email du parent pour l'étudiant
                phone=app.parent_phone,
                birth_date=birth_date,
                parent=parent_user,
                establishment=establishment
            )
            created_students.append(student)
        
        # Marquer la demande comme approuvée
        app.status = 'approved'
        app.processed_at = timezone.now()
        app.save()
        
        # Générer le token de réinitialisation de mot de passe
        token = default_token_generator.make_token(parent_user)
        uid = urlsafe_base64_encode(force_bytes(parent_user.pk))
        reset_url = request.build_absolute_uri(
            reverse('App:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        
        # Envoyer un email de confirmation au parent avec template HTML
        try:
            # Render HTML email template
            html_message = render_to_string('Mails/account_creation/parent_account_approved.html', {
                'parent_first_name': app.parent_first_name,
                'parent_last_name': app.parent_last_name,
                'students': students_list,
                'username': username,
                'parent_email': app.parent_email,
                'reset_url': reset_url,
            })
            
            # Plain text fallback - create students text
            students_text = ', '.join([f"{s['first_name']} {s['last_name']}" for s in students_list])
            plain_message = f'''
Bonjour {app.parent_first_name} {app.parent_last_name},

Nous avons le plaisir de vous informer que votre demande d'inscription pour {students_text} a été approuvée.

Vos identifiants de connexion :
- Nom d'utilisateur : {username}
- Email : {app.parent_email}

Pour activer votre compte et définir votre mot de passe, veuillez cliquer sur le lien suivant :
{reset_url}

Ce lien est valide pendant 7 jours. Si vous n'avez pas demandé ce compte, vous pouvez ignorer cet email.

Vous pourrez ensuite vous connecter à votre tableau de bord pour suivre les activités de votre enfant.

Cordialement,
L'équipe des Éclaireurs
            '''
            
            # Send email with both HTML and plain text
            email_msg = EmailMultiAlternatives(
                subject='Votre demande a été approuvée - Les Éclaireurs',
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[app.parent_email],
            )
            email_msg.attach_alternative(html_message, 'text/html')
            email_msg.send()
            
        except Exception as e:
            pass  # L'email peut échouer, mais on continue
        
        num_students = len(created_students)
        student_word = "étudiant" if num_students == 1 else "étudiants"
        messages.success(request, f'Demande de {app.parent_first_name} {app.parent_last_name} approuvée. Compte utilisateur et {num_students} {student_word} créé(s).')
        
    except Exception as e:
        messages.error(request, f'Erreur lors de la validation : {str(e)}')
    
    return redirect('App:admin_dashboard')

@login_required
@role_required('admin')
def reject_parent_application(request, app_id):
    """Rejeter une demande parent"""
    app = get_object_or_404(ParentApplication, id=app_id)
    app.status = 'rejected'
    app.processed_at = timezone.now()
    app.save()
    
    # Envoyer un email de notification
    try:
        send_mail(
            'Demande d\'inscription - Les Éclaireurs',
            f'''
            Bonjour {app.parent_first_name} {app.parent_last_name},
            
            Nous avons examiné votre demande d'inscription pour {app.student_first_name} {app.student_last_name}.
            
            Malheureusement, nous ne pouvons pas accepter votre demande pour le moment.
            Vous pouvez nous contacter pour plus d'informations.
            
            Cordialement,
            L'équipe des Éclaireurs
            ''',
            settings.DEFAULT_FROM_EMAIL,
            [app.parent_email],
            fail_silently=False,
        )
    except Exception as e:
        pass
    
    messages.info(request, f'Demande de {app.parent_first_name} {app.parent_last_name} rejetée.')
    return redirect('App:admin_dashboard')

@login_required
@role_required('admin')
def validate_partner_application(request, app_id):
    """Valider une demande de partenariat et créer l'établissement"""
    app = get_object_or_404(PartnerApplication, id=app_id)
    
    try:
        # Créer l'établissement partenaire avec les données du formulaire
        establishment = Establishment.objects.create(
            name=app.school_name,
            address=app.school_address,
            city='À définir',  # Valeur par défaut
            postal_code='00000',  # Valeur par défaut
            region='À définir',  # Valeur par défaut
            school_type='Lycée',  # Par défaut, peut être modifié
            contact_email=app.contact_email,
            contact_phone=app.contact_phone,
            is_partner=True,
            partnership_date=timezone.now().date()
        )
        
        # Marquer la demande comme approuvée
        app.status = 'approved'
        app.processed_at = timezone.now()
        app.save()
        
        # Envoyer un email de confirmation au contact avec template HTML
        try:
            # Render HTML email template
            html_message = render_to_string('Mails/account_creation/partner_account_approved.html', {
                'contact_name': app.contact_name,
                'school_name': app.school_name,
                'contact_email': app.contact_email,
                'contact_phone': app.contact_phone,
            })
            
            # Plain text fallback
            plain_message = f'''
Bonjour {app.contact_name},

Nous avons le plaisir de vous informer que votre demande de partenariat pour l'établissement {app.school_name} a été approuvée.

Votre établissement est maintenant officiellement partenaire de notre programme d'accompagnement scolaire.
Vous pouvez maintenant proposer des ateliers et accueillir nos intervenants.

Nous vous contacterons prochainement pour organiser une rencontre et définir les modalités de notre collaboration.

Cordialement,
L'équipe des Éclaireurs
            '''
            
            # Send email with both HTML and plain text
            email_msg = EmailMultiAlternatives(
                subject='Votre demande de partenariat a été approuvée - Les Éclaireurs',
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[app.contact_email],
            )
            email_msg.attach_alternative(html_message, 'text/html')
            email_msg.send()
            
        except Exception as e:
            pass  # L'email peut échouer, mais on continue
        
        messages.success(request, f'Partenariat avec {app.school_name} approuvé. Établissement créé automatiquement.')
        
    except Exception as e:
        messages.error(request, f'Erreur lors de la validation du partenariat : {str(e)}')
    
    return redirect('App:admin_dashboard')

@login_required
@role_required('admin')
def reject_partner_application(request, app_id):
    """Rejeter une demande de partenariat"""
    app = get_object_or_404(PartnerApplication, id=app_id)
    app.status = 'rejected'
    app.processed_at = timezone.now()
    app.save()
    
    # Envoyer un email de notification
    try:
        send_mail(
            'Demande de partenariat - Les Éclaireurs',
            f'''
            Bonjour {app.contact_name},
            
            Nous avons examiné votre demande de partenariat pour l'établissement {app.school_name}.
            
            Malheureusement, nous ne pouvons pas accepter votre demande pour le moment.
            Vous pouvez nous contacter pour plus d'informations ou renouveler votre demande ultérieurement.
            
            Cordialement,
            L'équipe des Éclaireurs
            ''',
            settings.DEFAULT_FROM_EMAIL,
            [app.contact_email],
            fail_silently=False,
        )
    except Exception as e:
        pass
    
    messages.info(request, f'Demande de partenariat avec {app.school_name} rejetée.')
    return redirect('App:admin_dashboard')

@login_required
@role_required('admin')
def validate_intervenant_application(request, app_id):
    """Valider une candidature intervenant et créer le compte utilisateur"""
    app = get_object_or_404(IntervenantApplication, id=app_id)
    
    try:
        # Créer le compte utilisateur intervenant
        username = f"{app.prenom.lower()}.{app.nom.lower()}"
        # Vérifier si le nom d'utilisateur existe déjà
        counter = 1
        original_username = username
        while User.objects.filter(username=username).exists():
            username = f"{original_username}{counter}"
            counter += 1
        
        # Créer l'utilisateur intervenant avec un mot de passe temporaire (sera rendu non utilisable)
        intervenant_user = User.objects.create_user(
            username=username,
            email=app.email,
            first_name=app.prenom,
            last_name=app.nom,
            role='intervenant',
            phone=app.telephone,
            is_validated=True,
            password=get_random_string(20)  # Mot de passe temporaire (sera rendu non utilisable)
        )
        # Définir un mot de passe non utilisable pour forcer la réinitialisation
        intervenant_user.set_unusable_password()
        intervenant_user.save()
        
        # Marquer la candidature comme approuvée
        app.status = 'approved'
        app.processed_at = timezone.now()
        app.save()
        
        # Générer le token de réinitialisation de mot de passe
        token = default_token_generator.make_token(intervenant_user)
        uid = urlsafe_base64_encode(force_bytes(intervenant_user.pk))
        reset_url = request.build_absolute_uri(
            reverse('App:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        
        # Envoyer un email de confirmation avec template HTML
        try:
            # Render HTML email template
            html_message = render_to_string('Mails/account_creation/intervenant_account_approved.html', {
                'prenom': app.prenom,
                'nom': app.nom,
                'username': username,
                'email': app.email,
                'reset_url': reset_url,
            })
            
            # Plain text fallback
            plain_message = f'''
Bonjour {app.prenom} {app.nom},

Nous avons le plaisir de vous informer que votre candidature pour devenir intervenant a été approuvée.

Vos identifiants de connexion :
- Nom d'utilisateur : {username}
- Email : {app.email}

Pour activer votre compte et définir votre mot de passe, veuillez cliquer sur le lien suivant :
{reset_url}

Ce lien est valide pendant 7 jours. Si vous n'avez pas demandé ce compte, vous pouvez ignorer cet email.

Vous pourrez ensuite vous connecter à votre espace intervenant pour commencer à animer des ateliers.

Bienvenue dans l'équipe des Éclaireurs !

Cordialement,
L'équipe des Éclaireurs
            '''
            
            # Send email with both HTML and plain text
            email_msg = EmailMultiAlternatives(
                subject='Votre candidature a été approuvée - Les Éclaireurs',
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[app.email],
            )
            email_msg.attach_alternative(html_message, 'text/html')
            email_msg.send()
            
        except Exception as e:
            pass  # L'email peut échouer, mais on continue
        
        messages.success(request, f'Candidature de {app.prenom} {app.nom} approuvée. Compte intervenant créé.')
        
    except Exception as e:
        messages.error(request, f'Erreur lors de la validation : {str(e)}')
    
    return redirect('App:admin_dashboard')

@login_required
@role_required('admin')
def reject_intervenant_application(request, app_id):
    """Rejeter une candidature intervenant"""
    app = get_object_or_404(IntervenantApplication, id=app_id)
    app.status = 'rejected'
    app.processed_at = timezone.now()
    app.save()
    
    # Envoyer un email de notification
    try:
        send_mail(
            'Candidature Intervenant - Les Éclaireurs',
            f'''
            Bonjour {app.prenom} {app.nom},
            
            Nous avons examiné votre candidature pour devenir intervenant au sein de notre association.
            
            Malheureusement, nous ne pouvons pas accepter votre candidature pour le moment.
            Cependant, nous vous encourageons à renouveler votre candidature ultérieurement.
            
            Vous pouvez nous contacter pour plus d'informations.
            
            Cordialement,
            L'équipe des Éclaireurs
            ''',
            settings.DEFAULT_FROM_EMAIL,
            [app.email],
            fail_silently=False,
        )
    except Exception as e:
        pass
    
    messages.info(request, f'Candidature de {app.prenom} {app.nom} rejetée.')
    return redirect('App:admin_dashboard')

@login_required
@role_required('admin')
def approve_enrollment(request, enrollment_id):
    """Approuver une inscription à un atelier"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    # Check if workshop is full
    workshop = enrollment.workshop
    confirmed_count = workshop.enrollments.filter(is_confirmed=True).count()
    
    if confirmed_count >= workshop.max_students:
        messages.error(request, f'L\'atelier "{workshop.title}" est complet ({workshop.max_students} places maximum).')
        return redirect('App:admin_dashboard')
    
    enrollment.is_confirmed = True
    enrollment.save()
    
    messages.success(request, f'Inscription de {enrollment.student.first_name} {enrollment.student.last_name} à l\'atelier "{workshop.title}" approuvée.')
    return redirect('App:admin_dashboard')

@login_required
@role_required('admin')
def reject_enrollment(request, enrollment_id):
    """Rejeter une inscription à un atelier"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    
    student_name = f'{enrollment.student.first_name} {enrollment.student.last_name}'
    workshop_title = enrollment.workshop.title
    
    # Delete the enrollment
    enrollment.delete()
    
    messages.info(request, f'Inscription de {student_name} à l\'atelier "{workshop_title}" rejetée et supprimée.')
    return redirect('App:admin_dashboard')

# Actions pour les parents
@login_required
@role_required('parent')
def enroll_student(request, workshop_id):
    """Inscrire un élève à un atelier"""
    workshop = get_object_or_404(Workshop, id=workshop_id)
    student_id = request.POST.get('student_id')
    
    if student_id:
        student = get_object_or_404(Student, id=student_id, parent=request.user)
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            workshop=workshop
        )
    
    return redirect('App:parent_dashboard')

@login_required
@role_required('parent')
def unenroll_student(request, enrollment_id):
    """Désinscrire un élève d'un atelier"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student__parent=request.user)
    
    # Delete the enrollment
    enrollment.delete()
    
    return redirect('App:parent_dashboard')

@login_required
@role_required('parent')
def download_document(request, document_id):
    """Download a document - parents can only download documents from workshops their children are enrolled in"""
    document = get_object_or_404(Document, id=document_id)
    
    # Check if the parent's children are enrolled in any of the document's workshops
    enrolled_workshop_ids = Enrollment.objects.filter(
        student__parent=request.user
    ).values_list('workshop_id', flat=True)
    
    # Check if document is associated with any of the enrolled workshops
    if not document.workshops.filter(id__in=enrolled_workshop_ids).exists():
        messages.error(request, "Vous n'avez pas accès à ce document.")
        return redirect('App:parent_dashboard')
    
    # Serve the file
    if document.file:
        file_path = document.file.path
        content_type, _ = mimetypes.guess_type(file_path)
        response = FileResponse(open(file_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
        return response
    else:
        messages.error(request, "Le fichier n'existe pas.")
        return redirect('App:parent_dashboard')

# Actions pour les intervenants
@login_required
@role_required('intervenant')
def mark_attendance(request, enrollment_id):
    """Marquer la présence d'un élève"""
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, workshop__intervenant=request.user)
    enrollment.is_confirmed = True
    enrollment.save()
    messages.success(request, f'Présence confirmée pour {enrollment.student.first_name}.')
    return redirect('App:intervenant_dashboard')

# Authentication Views
def user_login(request):
    """Vue de connexion utilisateur"""
    if request.user.is_authenticated:
        # Clear any old messages for already authenticated users
        list(messages.get_messages(request))  # This clears all messages
        
        # Rediriger vers le dashboard approprié selon le rôle
        if request.user.role == 'admin':
            return redirect('App:admin_dashboard')
        elif request.user.role == 'parent':
            return redirect('App:parent_dashboard')
        elif request.user.role == 'intervenant':
            return redirect('App:intervenant_dashboard')
        elif request.user.role == 'professeur':
            return redirect('App:professeur_dashboard')
        else:
            return redirect('App:home')
    
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to authenticate - check if input is email or username
        user = None
        
        # Check if the input looks like an email
        if '@' in username_or_email:
            # Try to find user by email first
            try:
                user_obj = User.objects.get(email=username_or_email)
                # Authenticate using the username (not email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        else:
            # Try to authenticate with username
            user = authenticate(request, username=username_or_email, password=password)
        
        if user is not None:
            # Clear any old messages before login
            list(messages.get_messages(request))  # This clears all messages
            
            login(request, user)
            
            # Rediriger vers le dashboard approprié
            if user.role == 'admin':
                return redirect('App:admin_dashboard')
            elif user.role == 'parent':
                return redirect('App:parent_dashboard')
            elif user.role == 'intervenant':
                return redirect('App:intervenant_dashboard')
            elif user.role == 'professeur':
                return redirect('App:professeur_dashboard')
            else:
                return redirect('App:home')
        else:
            messages.error(request, 'Nom d\'utilisateur, email ou mot de passe incorrect.')
    
    context = {
        'page_title': 'Connexion - Les Éclaireurs',
        'page_description': 'Connectez-vous à votre compte pour accéder à votre tableau de bord.',
    }
    return render(request, 'Auth/login.html', context)

def user_logout(request):
    """Vue de déconnexion utilisateur"""
    logout(request)
    return redirect('App:home')

@login_required
def user_profile(request):
    """Vue de profil utilisateur - affichage et modification des informations"""
    from .forms import UserProfileForm
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre profil a été mis à jour avec succès.')
            return redirect('App:user_profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'page_title': 'Mon Profil',
        'form': form,
        'user': request.user,
    }
    return render(request, 'Auth/profile.html', context)

# ==================== ATTENDANCE VIEWS ====================

@login_required
@role_required('intervenant')
def save_attendance(request):
    """Save attendance from the attendance report form"""
    if request.method == 'POST':
        workshop_id = request.POST.get('workshop_id')
        date_str = request.POST.get('date')
        
        if not workshop_id or not date_str:
            messages.error(request, 'Atelier et date requis.')
            return redirect('App:intervenant_attendance_report')
        
        # Verify workshop belongs to intervenant
        workshop = get_object_or_404(Workshop, id=workshop_id, intervenant=request.user)
        
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Get or create attendance sheet for this workshop + date
            attendance_sheet, created = AttendanceSheet.objects.get_or_create(
                workshop=workshop,
                date=date_obj,
                defaults={
                    'created_by': request.user
                }
            )
            
            # Check if sheet is finalized
            if attendance_sheet.is_finalized and not created:
                messages.warning(request, 'Cette feuille de présence est finalisée et ne peut plus être modifiée.')
                return redirect(f'/intervenant/attendance-report/?workshop={workshop_id}&date={date_str}')
            
            # Update session notes if provided
            session_notes = request.POST.get('session_notes', '')
            if session_notes != attendance_sheet.notes:
                attendance_sheet.notes = session_notes
                attendance_sheet.save()
            
            # Get all confirmed enrollments
            enrollments = workshop.enrollments.filter(is_confirmed=True)
            
            updated_count = 0
            for enrollment in enrollments:
                # Get status and notes for this enrollment from POST data
                status_key = f'status_{enrollment.id}'
                notes_key = f'notes_{enrollment.id}'
                
                status = request.POST.get(status_key)
                notes = request.POST.get(notes_key, '')
                
                if status:
                    Attendance.objects.update_or_create(
                        attendance_sheet=attendance_sheet,
                        enrollment=enrollment,
                        defaults={
                            'status': status,
                            'notes': notes
                        }
                    )
                    updated_count += 1
            
            if created:
                messages.success(request, f'Feuille de présence créée avec {updated_count} présence(s) pour le {date_obj.strftime("%d/%m/%Y")}.')
            else:
                messages.success(request, f'Feuille de présence mise à jour: {updated_count} présence(s) pour le {date_obj.strftime("%d/%m/%Y")}.')
            
            return redirect(f'/intervenant/attendance-report/?workshop={workshop_id}&date={date_str}')
            
        except ValueError:
            messages.error(request, 'Format de date invalide.')
            return redirect('App:intervenant_attendance_report')
        except Exception as e:
            messages.error(request, f'Erreur lors de l\'enregistrement: {str(e)}')
            return redirect('App:intervenant_attendance_report')
    
    return redirect('App:intervenant_attendance_report')

@login_required
@role_required('intervenant')
def finalize_attendance_sheet(request, sheet_id):
    """Finalize an attendance sheet (lock it)"""
    if request.method == 'POST':
        attendance_sheet = get_object_or_404(AttendanceSheet, id=sheet_id)
        
        # Verify the workshop belongs to the intervenant
        if attendance_sheet.workshop.intervenant != request.user:
            messages.error(request, 'Vous n\'avez pas la permission de finaliser cette feuille.')
            return redirect('App:intervenant_attendance_report')
        
        # Check if already finalized
        if attendance_sheet.is_finalized:
            messages.warning(request, 'Cette feuille de présence est déjà finalisée.')
        else:
            attendance_sheet.is_finalized = True
            attendance_sheet.save()
            messages.success(request, f'Feuille de présence finalisée avec succès. Elle ne peut plus être modifiée.')
        
        # Redirect back to the attendance report with the same workshop and date
        return redirect(f'/intervenant/attendance-report/?workshop={attendance_sheet.workshop.id}&date={attendance_sheet.date.strftime("%Y-%m-%d")}')
    
    return redirect('App:intervenant_attendance_report')


# ============================================================================
# DONATION VIEWS (HelloAsso Widget)
# ============================================================================

def get_hello_asso_token():
    """Retrieves an access token using Client Credentials flow"""
    import requests
    
    # Determine if we're using sandbox or production
    api_base = getattr(settings, 'HELLOASSO_API_BASE_URL', 'https://api.helloasso-sandbox.com/v5')
    
    if 'sandbox' in api_base.lower():
        auth_url = "https://api.helloasso-sandbox.com/oauth2/token"
    else:
        auth_url = "https://api.helloasso.com/oauth2/token"
    
    payload = {
        'client_id': getattr(settings, 'HELLOASSO_CLIENT_ID', ''),
        'client_secret': getattr(settings, 'HELLOASSO_CLIENT_SECRET', ''),
        'grant_type': 'client_credentials',
    }
    
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    response = requests.post(auth_url, data=payload, headers=headers)
    response.raise_for_status()
    return response.json().get('access_token')

def donation_form(request):
    """Redirect directly to HelloAsso donation form"""
    # Get HelloAsso configuration
    api_base = getattr(settings, 'HELLOASSO_API_BASE_URL', 'https://api.helloasso-sandbox.com/v5')
    org_slug = getattr(settings, 'HELLOASSO_ORGANIZATION_SLUG', 'w911006212')
    form_slug = getattr(settings, 'HELLOASSO_FORM_SLUG', '1')
    
    # Determine if we're using sandbox or production
    if 'sandbox' in api_base.lower():
        form_base_url = 'https://www.helloasso-sandbox.com'
    else:
        form_base_url = 'https://www.helloasso.com'
    
    # Build HelloAsso form URL
    redirect_url = f"{form_base_url}/associations/{org_slug}/formulaires/{form_slug}"
    
    print("\n🔗 REDIRECTING TO HELLOASSO FORM:")
    print(f"   Form URL: {redirect_url}")
    print(f"   Note: Webhook will create donation record after payment")
    
    # Redirect user directly to HelloAsso form
    # The webhook will create the donation record when payment is completed
    return redirect(redirect_url)


def donation_success(request):
    """Display success page after donation"""
    import requests
    from django.conf import settings
    
    donation_id = request.GET.get('donation_id')
    order_id = request.GET.get('orderId')  # HelloAsso sends this in the redirect URL
    checkout_intent_id = request.GET.get('checkoutIntentId')  # Also sent by HelloAsso
    donation = None
    donor_email = None
    
    if donation_id:
        try:
            donation = Donation.objects.get(id=donation_id)
            donation.status = 'completed'
            donation.payment_date = timezone.now()
            
            # Update transaction_id if we got it from URL
            if checkout_intent_id and not donation.transaction_id:
                donation.transaction_id = checkout_intent_id
            
            # Update order_id if we got it from URL
            if order_id and not donation.helloasso_order_id:
                donation.helloasso_order_id = order_id
            
            # Fetch order details from HelloAsso API to get receipt URLs
            # According to HelloAsso docs, receipt URLs are in /orders/{orderId} endpoint
            if donation.helloasso_order_id or order_id:
                try:
                    client_id = getattr(settings, 'HELLOASSO_CLIENT_ID', '')
                    client_secret = getattr(settings, 'HELLOASSO_CLIENT_SECRET', '')
                    api_base = getattr(settings, 'HELLOASSO_API_BASE_URL', 'https://api.helloasso-sandbox.com/v5')
                    
                    if client_id and client_secret:
                        # Get access token
                        token_url = api_base.replace('/v5', '') + "/oauth2/token"
                        token_data = {
                            'client_id': client_id,
                            'client_secret': client_secret,
                            'grant_type': 'client_credentials'
                        }
                        
                        token_response = requests.post(token_url, data=token_data)
                        
                        if token_response.status_code == 200:
                            access_token = token_response.json().get('access_token')
                            headers = {
                                'Authorization': f'Bearer {access_token}',
                                'Content-Type': 'application/json'
                            }
                            
                            # Fetch order details from /orders/{orderId} endpoint
                            order_id_to_fetch = order_id or donation.helloasso_order_id
                            if order_id_to_fetch:
                                order_url = f"{api_base}/orders/{order_id_to_fetch}"
                                order_response = requests.get(order_url, headers=headers)
                                
                                if order_response.status_code == 200:
                                    order_data = order_response.json()
                                    
                                    # Extract receipt URLs from payment object (receipt URLs are in payments array)
                                    payments = order_data.get('payments', [])
                                    if payments:
                                        payment = payments[0]  # Get first payment
                                        if not donation.helloasso_payment_id:
                                            donation.helloasso_payment_id = payment.get('id', '')
                                        
                                        # Receipt URLs are in the payment object
                                        donation.receipt_url = payment.get('paymentReceiptUrl', '')
                                        donation.tax_receipt_url = payment.get('fiscalReceiptUrl', '')
                                    
                                    # Update notes
                                    if not donation.notes:
                                        donation.notes = ''
                                    donation.notes += f'\nOrder fetched from /orders endpoint: {order_id_to_fetch}'
                                    if donation.receipt_url:
                                        donation.notes += f'\nReceipt URL: {donation.receipt_url}'
                                    if donation.tax_receipt_url:
                                        donation.notes += f'\nTax Receipt URL: {donation.tax_receipt_url}'
                                else:
                                    print(f"Error fetching order: {order_response.status_code} - {order_response.text}")
                            
                            # Fallback: Try to get order from checkout intent if we don't have orderId yet
                            if donation.transaction_id and not order_id_to_fetch:
                                org_slug = getattr(settings, 'HELLOASSO_ORGANIZATION_SLUG', 'w911006212')
                                checkout_url = f"{api_base}/organizations/{org_slug}/checkout-intents/{donation.transaction_id}"
                                checkout_response = requests.get(checkout_url, headers=headers)
                                
                                if checkout_response.status_code == 200:
                                    checkout_data = checkout_response.json()
                                    orders = checkout_data.get('orders', [])
                                    if orders:
                                        order = orders[0]
                                        donation.helloasso_order_id = order.get('id', '')
                                        
                                        # Try to fetch from /orders endpoint with the order ID we just got
                                        if donation.helloasso_order_id:
                                            order_url = f"{api_base}/orders/{donation.helloasso_order_id}"
                                            order_response = requests.get(order_url, headers=headers)
                                            if order_response.status_code == 200:
                                                order_data = order_response.json()
                                                
                                                # Extract receipt URLs from payment object
                                                payments = order_data.get('payments', [])
                                                if payments:
                                                    payment = payments[0]
                                                    donation.receipt_url = payment.get('paymentReceiptUrl', '')
                                                    donation.tax_receipt_url = payment.get('fiscalReceiptUrl', '')
                                                    if not donation.helloasso_payment_id:
                                                        donation.helloasso_payment_id = payment.get('id', '')
                                                
                except Exception as e:
                    # Log error but don't fail the success page
                    print(f"Error fetching HelloAsso order details: {str(e)}")
                    if not donation.notes:
                        donation.notes = ''
                    donation.notes += f'\nError fetching order details: {str(e)}'
            
            donation.save()
            donor_email = donation.donor_email
        except Donation.DoesNotExist:
            pass
    
    return render(request, 'Donations/donation_success.html', {
        'donation': donation,
        'donor_email': donor_email
    })


def donation_cancel(request):
    """Display cancel page when donation is cancelled"""
    donation_id = request.GET.get('donation_id')
    
    if donation_id:
        try:
            donation = Donation.objects.get(id=donation_id)
            donation.status = 'cancelled'
            donation.save()
        except Donation.DoesNotExist:
            pass
    
    return render(request, 'Donations/donation_cancel.html')


@csrf_exempt
def helloasso_webhook(request):
    """
    Webhook endpoint to receive HelloAsso notifications
    HelloAsso will send POST requests here when payments are made on forms
    """
    from django.http import JsonResponse
    import json
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests allowed'}, status=405)
    
    try:
        # Parse the JSON payload from HelloAsso
        payload = json.loads(request.body.decode('utf-8'))
        
        # Log the received webhook for debugging
        print("\n📨 HELLOASSO WEBHOOK RECEIVED:")
        print(f"   Event Type: {payload.get('eventType')}")
        print(f"   Data: {json.dumps(payload, indent=2)}")
        
        # Extract event type and data
        event_type = payload.get('eventType')
        data = payload.get('data', {})
        
        # Handle Order notification (payment completed on a form)
        if event_type == 'Order':
            # For Order event, data is directly in the 'data' object
            payer = data.get('payer', {})
            items = data.get('items', [])
            payments = data.get('payments', [])
            
            # Get order ID from items (the item ID is the order ID)
            order_id = str(items[0].get('id', '')) if items else ''
            
            # Get amount from items
            amount = items[0].get('amount', 0) if items else 0
            
            # Extract payer information
            payer_first_name = payer.get('firstName', '')
            payer_last_name = payer.get('lastName', '')
            payer_email = payer.get('email', '')
            payer_full_name = f"{payer_first_name} {payer_last_name}".strip()
            
            # Payment information
            payment_id = ''
            payment_receipt_url = ''
            tax_receipt_url = ''
            payment_state = ''
            
            if payments:
                payment = payments[0]
                payment_id = str(payment.get('id', ''))
                payment_receipt_url = payment.get('paymentReceiptUrl', '')
                tax_receipt_url = payment.get('fiscalReceiptUrl', '')
                payment_state = payment.get('state', '')
            
            # Form information (not available in Order event, will use defaults)
            form_slug = ''
            form_type = 'Donation'
            
            print(f"   Order ID: {order_id}")
            print(f"   Payer: {payer_full_name} ({payer_email})")
            print(f"   Amount: {amount/100}€")
            print(f"   Payment State: {payment_state}")
            print(f"   Form: {form_type}/{form_slug}")
            if tax_receipt_url:
                print(f"   📄 Tax Receipt: {tax_receipt_url}")
            
            # Try to find matching donation in database
            # We can match by:
            # 1. Amount and email (if available)
            # 2. Recent pending donations
            
            donation = None
            
            # First try: Find by email and amount (most recent pending)
            if payer_email:
                try:
                    donation = Donation.objects.filter(
                        donor_email=payer_email,
                        amount=amount/100,  # Convert centimes to euros
                        status='pending'
                    ).order_by('-donation_date').first()
                except Exception as e:
                    print(f"   Error finding donation by email: {str(e)}")
            
            # Second try: Find by amount only (most recent pending)
            if not donation:
                try:
                    donation = Donation.objects.filter(
                        amount=amount/100,
                        status='pending',
                        payment_method='HelloAsso'
                    ).order_by('-donation_date').first()
                except Exception as e:
                    print(f"   Error finding donation by amount: {str(e)}")
            
            # If we found a matching donation, update it
            if donation:
                donation.status = 'completed'
                donation.payment_date = timezone.now()
                donation.helloasso_order_id = order_id or ''
                donation.helloasso_payment_id = payment_id or ''
                donation.receipt_url = payment_receipt_url or ''
                donation.tax_receipt_url = tax_receipt_url or ''
                
                # ALWAYS update donor information with HelloAsso data (more reliable)
                # The payer info from HelloAsso is what was actually validated during payment
                if payer_full_name:
                    donation.donor_name = payer_full_name
                if payer_email:
                    donation.donor_email = payer_email
                
                # Add webhook info to notes
                if donation.notes:
                    donation.notes += f'\n'
                donation.notes += f'Webhook received: Order {order_id or "N/A"}, Payment {payment_state}'
                
                donation.save()
                
                print(f"   ✅ Donation #{donation.id} updated successfully")
            else:
                # No matching donation found - create a new one
                print(f"   ⚠️ No matching donation found, creating new record")
                donation = Donation.objects.create(
                    donor_name=payer_full_name or 'Anonyme',
                    donor_email=payer_email or '',
                    amount=amount/100 if amount else 0,
                    donation_type='one_time',
                    status='completed',
                    payment_date=timezone.now(),
                    payment_method='HelloAsso',
                    helloasso_order_id=order_id or '',
                    helloasso_payment_id=payment_id or '',
                    receipt_url=payment_receipt_url or '',
                    tax_receipt_url=tax_receipt_url or '',
                    notes=f'Created from webhook: Order {order_id or "N/A"}, Form {form_type}/{form_slug}'
                )
                print(f"   ✅ New donation #{donation.id} created from webhook")
        
        # Handle Payment notification
        elif event_type == 'Payment':
            # For Payment event, data has 'order' and 'payer' at the same level
            order_data = data.get('order', {})
            payer = data.get('payer', {})
            items = data.get('items', [])
            
            order_id = str(order_data.get('id', ''))
            form_slug = order_data.get('formSlug', '')
            form_type = order_data.get('formType', '')
            
            # Extract payer information
            payer_first_name = payer.get('firstName', '')
            payer_last_name = payer.get('lastName', '')
            payer_email = payer.get('email', '')
            payer_full_name = f"{payer_first_name} {payer_last_name}".strip()
            
            # Get amount from items
            amount = items[0].get('amount', 0) if items else 0
            
            # Payment info (at data level for Payment event)
            payment_id = str(data.get('id', ''))
            payment_state = data.get('state', '')
            payment_receipt_url = data.get('paymentReceiptUrl', '')
            tax_receipt_url = data.get('fiscalReceiptUrl', '')
            
            print(f"   Payment {payment_id}: {payment_state}")
            print(f"   Order ID: {order_id}")
            print(f"   Payer: {payer_full_name} ({payer_email})")
            print(f"   Amount: {amount/100}€")
            print(f"   Form: {form_type}/{form_slug}")
            if tax_receipt_url:
                print(f"   📄 Tax Receipt: {tax_receipt_url}")
            
            # Try to find and update existing donation
            donation = None
            
            # Try to find by order_id first (most reliable)
            if order_id:
                try:
                    donation = Donation.objects.filter(
                        helloasso_order_id=order_id
                    ).first()
                except Exception as e:
                    print(f"   Error finding donation by order_id: {str(e)}")
            
            # Try by email and amount if not found
            if not donation and payer_email and amount:
                try:
                    donation = Donation.objects.filter(
                        donor_email=payer_email,
                        amount=amount/100,
                        status__in=['pending', 'completed']
                    ).order_by('-donation_date').first()
                except Exception as e:
                    print(f"   Error finding donation by email: {str(e)}")
            
            if donation:
                # Update with payment information (especially tax receipt)
                donation.status = 'completed'
                donation.payment_date = timezone.now()
                if payment_id:
                    donation.helloasso_payment_id = payment_id
                if payment_receipt_url:
                    donation.receipt_url = payment_receipt_url
                if tax_receipt_url:
                    donation.tax_receipt_url = tax_receipt_url
                
                # Update donor information with HelloAsso data
                if payer_full_name:
                    donation.donor_name = payer_full_name
                if payer_email:
                    donation.donor_email = payer_email
                
                if donation.notes:
                    donation.notes += f'\n'
                donation.notes += f'Payment webhook: {payment_id}, State: {payment_state}'
                
                donation.save()
                print(f"   ✅ Donation #{donation.id} updated with payment info")
            else:
                print(f"   ⚠️ No matching donation found for Payment event")
        
        # Return success response to HelloAsso
        return JsonResponse({
            'status': 'success',
            'message': 'Webhook processed successfully'
        }, status=200)
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': 'Internal server error'}, status=500)


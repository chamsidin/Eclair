from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'App'

urlpatterns = [
    path('', views.home, name='home'),
    path('inscriptions/', views.main_formulaires, name='main_formulaires'),
    path('inscription-parent/', views.parent_inscription, name='parent_inscription'),
    path('inscription-parent/success/', views.parent_inscription_success, name='parent_inscription_success'),
    path('demande-partenariat/', views.proviseur_inscription, name='proviseur_inscription'),
    path('demande-partenariat/success/', views.proviseur_inscription_success, name='proviseur_inscription_success'),
    path('devenir-intervenant/', views.intervenant_inscription, name='intervenant_inscription'),
    path('devenir-intervenant/success/', views.intervenant_inscription_success, name='intervenant_inscription_success'),
    
    # Dashboard URLs
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/parent/', views.parent_dashboard, name='parent_dashboard'),
    path('dashboard/parent/add-child/', views.add_child, name='add_child'),
    path('dashboard/intervenant/', views.intervenant_dashboard, name='intervenant_dashboard'),
    path('dashboard/professeur/', views.professeur_dashboard, name='professeur_dashboard'),
    
    # Professeur actions
    path('professeur/documents/', views.professeur_documents, name='professeur_documents'),
    path('professeur/attendance-sheets/', views.professeur_attendance_sheets, name='professeur_attendance_sheets'),
    
    # Admin list views
    path('dashboard-admin/users/', views.admin_users_list, name='admin_users_list'),
    path('dashboard-admin/students/', views.admin_students_list, name='admin_students_list'),
    path('dashboard-admin/workshops/', views.admin_workshops_list, name='admin_workshops_list'),
    path('dashboard-admin/workshops/edit/<int:workshop_id>/', views.admin_workshop_edit, name='admin_workshop_edit'),
    path('dashboard-admin/workshops/delete/<int:workshop_id>/', views.admin_workshop_delete, name='admin_workshop_delete'),
    path('dashboard-admin/establishments/', views.admin_establishments_list, name='admin_establishments_list'),
    path('dashboard-admin/donations/', views.admin_donations_list, name='admin_donations_list'),
    path('dashboard-admin/get-rooms/', views.get_rooms_by_establishment, name='get_rooms_by_establishment'),
    
    # AJAX endpoints
    path('ajax/workshop-details/<int:workshop_id>/', views.get_workshop_details, name='get_workshop_details'),
    path('ajax/child-details/<int:child_id>/', views.get_child_details, name='get_child_details'),
    path('ajax/parent-application-details/<int:application_id>/', views.get_parent_application_details, name='get_parent_application_details'),
    path('ajax/intervenant-application-details/<int:application_id>/', views.get_intervenant_application_details, name='get_intervenant_application_details'),
    path('ajax/partnership-application-details/<int:application_id>/', views.get_partnership_application_details, name='get_partnership_application_details'),
    path('ajax/user-details/<int:user_id>/', views.get_user_details, name='get_user_details'),
    path('ajax/intervenant-workshop-details/<int:workshop_id>/', views.get_intervenant_workshop_details, name='get_intervenant_workshop_details'),
    path('ajax/enrollment-details/<int:enrollment_id>/', views.get_enrollment_details, name='get_enrollment_details'),
    path('ajax/workshop-enrollments/<int:workshop_id>/', views.get_workshop_enrollments, name='get_workshop_enrollments'),
    
    # Admin actions
    path('dashboard-admin/validate-user/<int:user_id>/', views.validate_user, name='validate_user'),
    path('dashboard-admin/validate-parent-app/<int:app_id>/', views.validate_parent_application, name='validate_parent_application'),
    path('dashboard-admin/reject-parent-app/<int:app_id>/', views.reject_parent_application, name='reject_parent_application'),
    path('dashboard-admin/validate-partner-app/<int:app_id>/', views.validate_partner_application, name='validate_partner_application'),
    path('dashboard-admin/reject-partner-app/<int:app_id>/', views.reject_partner_application, name='reject_partner_application'),
    path('dashboard-admin/validate-intervenant-app/<int:app_id>/', views.validate_intervenant_application, name='validate_intervenant_application'),
    path('dashboard-admin/reject-intervenant-app/<int:app_id>/', views.reject_intervenant_application, name='reject_intervenant_application'),
    path('dashboard-admin/approve-enrollment/<int:enrollment_id>/', views.approve_enrollment, name='approve_enrollment'),
    path('dashboard-admin/reject-enrollment/<int:enrollment_id>/', views.reject_enrollment, name='reject_enrollment'),
    
    # Parent actions
    path('parent/enroll/<int:workshop_id>/', views.enroll_student, name='enroll_student'),
    path('parent/unenroll/<int:enrollment_id>/', views.unenroll_student, name='unenroll_student'),
    path('parent/download-document/<int:document_id>/', views.download_document, name='download_document'),
    path('parent/attendance-sheets/', views.parent_attendance_sheets, name='parent_attendance_sheets'),
    
    # Intervenant actions
    path('intervenant/mark-attendance/<int:enrollment_id>/', views.mark_attendance, name='mark_attendance'),
    path('intervenant/attendance-report/', views.intervenant_attendance_report, name='intervenant_attendance_report'),
    path('intervenant/save-attendance/', views.save_attendance, name='save_attendance'),
    path('intervenant/finalize-attendance/<int:sheet_id>/', views.finalize_attendance_sheet, name='finalize_attendance_sheet'),
    path('intervenant/documents/', views.intervenant_documents, name='intervenant_documents'),
    path('intervenant/delete-document/<int:document_id>/', views.delete_document, name='delete_document'),
    
    # Authentication
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('profile/', views.user_profile, name='user_profile'),
    
    # Password reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='Auth/password_reset.html',
        email_template_name='Mails/password_reset_email.html',
        html_email_template_name='Mails/password_reset_email.html',
        subject_template_name='Mails/password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='Auth/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='Auth/password_reset_confirm.html',
        success_url='/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='Auth/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Donation URLs (HelloAsso API Integration)
    path('faire-un-don/', views.donation_form, name='donation_form'),
    path('donation/', views.donation_form, name='donation_widget'),  # Legacy URL
    path('donation/success/', views.donation_success, name='donation_success'),
    path('donation/cancel/', views.donation_cancel, name='donation_cancel'),
    path('webhook/helloasso/', views.helloasso_webhook, name='helloasso_webhook'),
]

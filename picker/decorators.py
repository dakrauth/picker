from django.contrib.auth.decorators import user_passes_test

#-------------------------------------------------------------------------------
staff_member_required = user_passes_test(
    lambda u: u.is_authenticated() and u.is_active and u.is_staff
)


#-------------------------------------------------------------------------------
superuser_required = user_passes_test(
    lambda u: u.is_authenticated() and u.is_active and u.is_superuser
)


#-------------------------------------------------------------------------------
management_user_required = user_passes_test(
    lambda u: u.is_authenticated() and u.is_active and u.is_superuser

)
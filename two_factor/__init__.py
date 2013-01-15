from django.conf import settings
from django.contrib.admin import sites
from django.shortcuts import redirect


#monkey-patch admin login
def redirect_admin_login(self, request):
    return redirect(settings.LOGIN_URL)

sites.AdminSite.login = redirect_admin_login

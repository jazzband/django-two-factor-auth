from django.conf import settings
from django.contrib.admin import sites
from django.views.generic.simple import redirect_to

#monkey-patch admin login
def redirect_admin_login(self, request):
    return redirect_to(request, settings.LOGIN_URL)

sites.AdminSite.login = redirect_admin_login

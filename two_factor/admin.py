from django.contrib import admin
from two_factor.models import VerifiedComputer, Secret

admin.site.register(VerifiedComputer)
admin.site.register(Secret)

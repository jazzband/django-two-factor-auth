from django.contrib import admin
from two_factor.models import VerifiedComputer, Token

admin.site.register(VerifiedComputer)
admin.site.register(Token)

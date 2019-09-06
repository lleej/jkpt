from django.contrib import admin

from common.models import Highway, Section
# Register your models here.


@admin.register(Highway)
class HighwayAdmin(admin.ModelAdmin):
    readonly_fields = ('created_time',)

admin.site.register(Section)
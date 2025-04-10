from django.contrib import admin
from .models import DDIProfile
from .models import State
from .models import DDIPhases
from .models import DDIStatus


class DdiprofileAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'start_date', 'planned_duration', 'sit_start_date', 'sit_end_date', 'uat_start_date', 'uat_end_date', 'go_live_date')


class DdistatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'current_phase', 'sit_complete', 'uat_complete','remarks')


admin.site.register(DDIProfile, DdiprofileAdmin)
admin.site.register(State)
admin.site.register(DDIPhases)
admin.site.register(DDIStatus, DdistatusAdmin)

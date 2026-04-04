from django.contrib import admin
from .models import Trade, Strategy
from django.contrib import admin
from .models import SimulationHistory

admin.site.register(Trade)
admin.site.register(Strategy)
from django.contrib import admin

# Register your models here.


from django.contrib import admin
from .models import SimulationHistory

@admin.register(SimulationHistory)
class SimulationHistoryAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "label", "created_at"]
    search_fields = ["label", "user__username"]
    list_filter = ["created_at"]
    ordering = ["-created_at"]

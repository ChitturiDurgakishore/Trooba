# myapp/admin.py
from django.contrib import admin
from django.db import models # Import models to reference field types
from django import forms # Import forms for widgets
from .models import Prompt

@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ('type', )
    search_fields = ('prompt', 'type')
    list_filter = ('type',)

    # Override widgets for specific field types within this admin
    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs={'rows': 18, 'cols': 150})}, # Affects all TextFields
        models.CharField: {'widget': forms.TextInput(attrs={'size': 60})},     # Affects all CharFields
    }

    def prompt_excerpt(self, obj):
        return obj.prompt[:100] + '...' if len(obj.prompt) > 100 else obj.prompt
    prompt_excerpt.short_description = 'Prompt Content'
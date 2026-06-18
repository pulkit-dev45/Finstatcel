from django.contrib import admin
from .models import StatementUpload

@admin.register(StatementUpload)
class StatementUploadAdmin(admin.ModelAdmin):
    list_display = ['id', 'filename', 'uploaded_at', 'processed']
    list_filter = ['processed']

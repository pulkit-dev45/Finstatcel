import json
import os
from django.conf import settings
from django.db import models

class StatementUpload(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    pdf_file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    excel_file = models.FileField(upload_to='exports/', blank=True, null=True)
    processed = models.BooleanField(default=False)
    processing = models.BooleanField(default=False)
    row_count = models.IntegerField(null=True, blank=True)
    progress = models.IntegerField(default=0)
    preview_json = models.TextField(null=True, blank=True)

    def filename(self):
        return os.path.splitext(os.path.basename(self.pdf_file.name))[0]

    def get_preview_rows(self):
        if self.preview_json:
            return json.loads(self.preview_json)
        return []

    class Meta:
        ordering = ['-uploaded_at']

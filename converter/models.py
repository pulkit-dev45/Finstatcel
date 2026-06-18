import os
from django.db import models

class StatementUpload(models.Model):
    pdf_file = models.FileField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    excel_file = models.FileField(upload_to='exports/', blank=True, null=True)
    processed = models.BooleanField(default=False)

    def filename(self):
        return os.path.splitext(os.path.basename(self.pdf_file.name))[0]

    class Meta:
        ordering = ['-uploaded_at']

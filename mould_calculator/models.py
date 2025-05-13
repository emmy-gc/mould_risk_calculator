from django.db import models
from django.contrib.auth.models import User


class MouldAnalysis(models.Model):
    user =models.ForeignKey(User, on_delete=models.CASCADE, null =True, blank=True )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=200)
    file= models.FileField(upload_to='uploads/')
    temperature= models.FloatField()
    humidity = models.FloatField()
    mould_index = models.FloatField()
    risk_level = models.CharField(max_length=100)
    risk_message=models.TextField()

    def __str__(self):
        return f"{self.filename} ({self.risk_level})"
    
    








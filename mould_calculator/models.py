from django.db import models

class MouldData(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField()
    humidity = models.FloatField()
    mould_index = models.FloatField()


    def __str__(self):
        return f"{self.timestamp} | Mould Index {self.mould_index:.2f}"

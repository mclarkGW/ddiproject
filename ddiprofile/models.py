from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


# Building Database Fields to Hold ADO Query Info
class Initiative(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    workitemtype = models.CharField(max_length=50)
    currentphase = models.CharField(max_length=100, blank=True, null=True)
    golivedate = models.DateField(blank=True, null=True)
    months = models.IntegerField(blank=True, null=True)
    sitcmpl = models.DecimalField(default=0, decimal_places=0, max_digits=3, blank=True, null=True)
    sitstart = models.DateField(blank=True, null=True)
    start = models.DateField(blank=True, null=True)
    uatcmpl = models.DecimalField(default=0, decimal_places=0, max_digits=3, blank=True, null=True)
    uatstart = models.DateField(blank=True, null=True)

class Epic(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    workitemtype = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    areapath = models.CharField(max_length=255, blank=True, null=True)
    iterationpath = models.CharField(max_length=255, blank=True, null=True)
    enddate = models.DateField(blank=True, null=True)
    statuschoice = models.CharField(max_length=100, blank=True, null=True)
    statustextbox = models.TextField(blank=True, null=True)
    requiredbdate = models.DateField(blank=True, null=True)
    epiccategory = models.CharField(max_length=100, blank=True, null=True)
    created_date = models.DateField(blank=True, null=True)
    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name='epics')

class LastRefreshed(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class State(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class DDIProfile(models.Model):
    name = models.CharField(max_length=255)
    state = models.ForeignKey('State', on_delete=models.PROTECT)
    start_date = models.DateField()
    planned_duration = models.CharField(max_length=50)
    sit_start_date = models.DateField()
    sit_end_date = models.DateField()
    uat_start_date = models.DateField()
    uat_end_date = models.DateField()
    go_live_date = models.DateField()
    history = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    # New Line of Validation Code

    def clean(self):
        if self.sit_end_date < self.sit_start_date:
            raise ValidationError({'sit_end_date': "SIT End Date cannot be before SIT Start Date"})
        if self.uat_end_date < self.uat_start_date:
            raise ValidationError({'uat_end_date': "SIT End Date cannot be before SIT Start Date"})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DDIPhases(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class DDIStatus(models.Model):
    name = models.ForeignKey('DDIProfile', on_delete=models.PROTECT)
    current_phase = models.ForeignKey('DDIPhases', on_delete=models.PROTECT)
    date = models.DateField(default=timezone.now)
    sit_complete = models.DecimalField(default=0, decimal_places=0, max_digits=3)
    uat_complete = models.DecimalField(default=0, decimal_places=0, max_digits=3)
    remarks = models.TextField(blank=True, null=True)

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

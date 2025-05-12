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
    clientaccounts = models.CharField(max_length=255, blank=True, null=True)
    solutiongotomarket = models.CharField(max_length=255, blank=True, null=True)
    deliverysupportleader = models.CharField(max_length=255, blank=True, null=True)
    deliverysupportleadermail = models.CharField(max_length=255, blank=True, null=True)
    deliverysupportseniorleader = models.CharField(max_length=255, blank=True, null=True)
    deliverysupportseniorleadermail = models.CharField(max_length=255, blank=True, null=True)
    deliverysupportdirector = models.CharField(max_length=255, blank=True, null=True)
    deliverysupportdirectormail = models.CharField(max_length=255, blank=True, null=True)

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
    requiredbydate = models.DateField(blank=True, null=True)
    epiccategory = models.CharField(max_length=100, blank=True, null=True)
    created_date = models.DateField(blank=True, null=True)
    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name='epics')

class ChangeRequest(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    workitemtype = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    areapath = models.CharField(max_length=255, blank=True, null=True)
    iterationpath = models.CharField(max_length=255, blank=True, null=True)
    clientaccounts = models.CharField(max_length=255, blank=True, null=True)
    solutiongotomarket = models.CharField(max_length=255, blank=True, null=True)
    targetdate = models.DateField(blank=True, null=True)
    highlevelestimate = models.CharField(max_length=255, blank=True, null=True)
    tt_initiative = models.CharField(max_length=255, blank=True, null=True)
    tt_workdescription = models.CharField(max_length=255, blank=True, null=True)
    tt_workcategory = models.CharField(max_length=255, blank=True, null=True)
    tt_capwbs = models.CharField(max_length=255, blank=True, null=True)
    tt_expwbs = models.CharField(max_length=255, blank=True, null=True)
    tt_onshorewbs = models.CharField(max_length=255, blank=True, null=True)
    tt_offshorewbs = models.CharField(max_length=255, blank=True, null=True)
    createddate = models.DateField(blank=True, null=True)
    requiredbydate = models.DateField(blank=True, null=True)
    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name='change_requests')

class Feature(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    workitemtype = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    areapath = models.CharField(max_length=255, blank=True, null=True)
    iterationpath = models.CharField(max_length=255, blank=True, null=True)
    clientaccounts = models.CharField(max_length=255, blank=True, null=True)
    solutiongotomarket = models.CharField(max_length=255, blank=True, null=True)
    startdate = models.DateField(blank=True, null=True)
    targetdate = models.DateField(blank=True, null=True)
    highlevelestimate = models.CharField(max_length=255, blank=True, null=True)
    tt_initiative = models.CharField(max_length=255, blank=True, null=True)
    tt_workcategory = models.CharField(max_length=255, blank=True, null=True)
    tt_workdescription = models.CharField(max_length=255, blank=True, null=True)
    tt_capwbs = models.CharField(max_length=255, blank=True, null=True)
    tt_expwbs = models.CharField(max_length=255, blank=True, null=True)
    tt_onshorewbs = models.CharField(max_length=255, blank=True, null=True)
    tt_offshorewbs = models.CharField(max_length=255, blank=True, null=True)
    createddate = models.DateField(blank=True, null=True)
    cr_related = models.ForeignKey(ChangeRequest, on_delete=models.CASCADE, related_name='features')

class UserStory(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)
    workitemtype = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    areapath = models.CharField(max_length=255, blank=True, null=True)
    iterationpath = models.CharField(max_length=255, blank=True, null=True)
    clientaccounts = models.CharField(max_length=255, blank=True, null=True)
    storypoints = models.CharField(max_length=255, blank=True, null=True)
    tt_initiative = models.CharField(max_length=255, blank=True, null=True)
    tt_workcategory = models.CharField(max_length=255, blank=True, null=True)
    tt_workdescription = models.CharField(max_length=255, blank=True, null=True)
    tt_capwbs = models.CharField(max_length=255, blank=True, null=True)
    tt_expwbs = models.CharField(max_length=255, blank=True, null=True)
    tt_onshorewbs = models.CharField(max_length=255, blank=True, null=True)
    tt_offshorewbs = models.CharField(max_length=255, blank=True, null=True)
    createddate = models.DateField(blank=True, null=True)
    feature_related = models.ForeignKey(Feature, on_delete=models.CASCADE,related_name='user_stories')

class LastRefreshed(models.Model):
    id = models.IntegerField(primary_key=True)
    title = models.CharField(max_length=255)

class Iteration(models.Model):
    iteration_id = models.CharField(max_length=100, unique=True)  # Unique ID from Azure
    name = models.CharField(max_length=255)  # Iteration name
    path = models.CharField(max_length=255)  # Iteration path
    start_date = models.DateField(null=True, blank=True)  # Start date
    finish_date = models.DateField(null=True, blank=True)  # Finish date
    scriptupdated = models.CharField(max_length=255)  # Last updated timestamp
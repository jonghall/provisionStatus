from django.db import models
from django.template.defaultfilters import slugify
from django.contrib.auth.models import User


class UserProfile(models.Model):
    # This line is required. Links UserProfile to a User model instance.
    user = models.OneToOneField(User)

    # The additional attributes we wish to include.
    website = models.URLField(blank=True)
    picture = models.ImageField(upload_to='profile_images', blank=True)

    # Override the __unicode__() method to return out something meaningful!
    def __unicode__(self):
        return self.user.username

#class VirtualGuests(models.Model)
#        guestID = models.CharField(max_length=12, unique=True)
#        provisionDate = models.DateTimeField()
#        hostName = models.CharField(max_length=32)
#        activeTicketCount = models.IntegerField(default=0)
#        lastTransaction = models.default()
#        activeTransaction = models.default()
#        activeTransactions = models.default()
#        datacenter = models.CharField(max_lenth=12)
#        serverRoom = models.charField(max_length=12)
#        powerOnDate =  models.DateTimeField()
#        status = models.CharField(max_length=12)

#       def __str__(self):
#               return self.name

#class Transactions
#        guestID = models.ForeignKey(VirtualGuests)



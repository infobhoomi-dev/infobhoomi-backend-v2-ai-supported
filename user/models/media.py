from django.db import models
from django.contrib.auth.models import AbstractUser, PermissionsMixin, BaseUserManager
from django.contrib.gis.db import models as gismodels
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db.models import UniqueConstraint


#_______________________________________________ Attrib Panel Image Upload Model ________________________________________________
class Attrib_Image_Model(models.Model):
    image_id = models.AutoField(primary_key=True)

    su_id = models.OneToOneField('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    user_id = models.IntegerField(null=False)
    file_path = models.FileField(upload_to='documents/images', null=True)

    status = models.BooleanField(null=False, default=True)
    remark = models.CharField(max_length=255, null=True)

    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
            managed = True
            db_table = 'attrib_panel_images'

#_______________________________________________ Messages Model _________________________________________________________________
class Messages_Model(models.Model):
    msg_id = models.AutoField(primary_key=True)

    user_id_sender = models.IntegerField(null=False)
    date_sent = models.DateTimeField(auto_now_add=True)
    subject = models.CharField(max_length=255, null=False)
    content = models.TextField(null=False)

    user_id_receiver = models.IntegerField(null=False)
    view_status = models.BooleanField(null=False, default=False)
    date_viewed = models.DateTimeField(null=True) # Automatically update this field in the backend when view_status is patched to True
    done_status = models.BooleanField(null=False, default=False)
    hide_status = models.BooleanField(null=False, default=False)

    file_path = models.FileField(upload_to='documents/message_attachements', null=True)

    class Meta:
            managed = True
            db_table = 'messages'

#_______________________________________________ Inquiries Model ________________________________________________________________
class Inquiries_Model(models.Model):
    inq_id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    user_id_creator = models.IntegerField(null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    inquiry_type = models.CharField(max_length=255, null=False)
    content = models.TextField(null=True)

    user_id_assigned = models.IntegerField(null=False)
    view_status = models.BooleanField(null=False, default=False)
    date_viewed = models.DateTimeField(null=True) # Automatically update this field in the backend when view_status is patched to True
    done_status = models.BooleanField(null=False, default=False)
    hide_status = models.BooleanField(null=False, default=False)

    class Meta:
            managed = True
            db_table = 'Inquiries'

#_______________________________________________ Reminders Model ________________________________________________________________
class Reminders_Model(models.Model):
    rmd_id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    user_id_creator = models.IntegerField(null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    reminder_type = models.CharField(max_length=255, null=False)
    content = models.TextField(null=True)
    date_remind = models.DateTimeField(null=False)

    done_status = models.BooleanField(null=False, default=False)
    hide_status = models.BooleanField(null=False, default=False)

    class Meta:
            managed = True
            db_table = 'reminders'

#_______________________________________________ Tags Model _____________________________________________________________________
class Tags_Model(models.Model):
    tag_id = models.AutoField(primary_key=True)

    su_id = models.ForeignKey('LA_Spatial_Unit_Model', on_delete=models.CASCADE, db_column='su_id', to_field='su_id')

    user_id_creator = models.IntegerField(null=False)
    date_created = models.DateTimeField(auto_now_add=True)
    tag_type = models.CharField(max_length=255, null=False)
    content = models.TextField(null=True)

    active_status = models.BooleanField(null=False, default=True)
    deleted_user = models.CharField(max_length=255, null=True)
    date_deleted = models.DateTimeField(null=True)

    class Meta:
            managed = True
            db_table = 'tags'

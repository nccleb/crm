from django.db import models
from django.contrib.auth.models import User
from team.models import Team
from django.core.exceptions import ValidationError


def only_int(value): 
    if value.isdigit()==False:
        raise ValidationError('ID contains characters')

class Client(models.Model):
   
    
    team = models.ForeignKey(Team, related_name='clients', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(validators=[only_int],null=True, max_length=254, blank=True, unique=True)
    email = models.EmailField()
    description = models.TextField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, related_name='clients', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ('name',)
  
    def __str__(self):
        return self.name



class Comment(models.Model):
    team = models.ForeignKey(Team, related_name='client_comments', on_delete=models.CASCADE)
    client = models.ForeignKey(Client, related_name='comments', on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, related_name='client_comments', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.created_by.username
    

class ClientFile(models.Model):
    team = models.ForeignKey(Team, related_name='client_files', on_delete=models.CASCADE)
    client = models.ForeignKey(Client, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='clientfiles')
    created_by = models.ForeignKey(User, related_name='client_files', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.created_by.username   
# Generated by Django 4.0.5 on 2022-06-10 07:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('album', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysisresult',
            name='field3',
            field=models.CharField(blank=True, default='', max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='analysisresult',
            name='location',
            field=models.CharField(blank=True, default='', max_length=100, null=True),
        ),
    ]
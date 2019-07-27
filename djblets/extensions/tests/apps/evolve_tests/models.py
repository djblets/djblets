from __future__ import unicode_literals

from django.db import models


class TestEvolveExtensionModel(models.Model):
    test_field = models.CharField(max_length=16)
    new_field = models.IntegerField(default=42)

    class Meta(object):
        app_label = 'evolve_tests'
        db_table = 'evolve_tests_testevolveextensionmodel'

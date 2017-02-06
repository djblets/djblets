from __future__ import unicode_literals

from django.db import models


class TestExtensionModel(models.Model):
    test_field = models.CharField(max_length=16)

    class Meta(object):
        app_label = 'model_tests'
        db_table = 'model_tests_testextensionmodel'

from django.contrib.auth.models import User
from django.db import models


class MyTestExtensionModel(models.Model):
    test_field = models.CharField(max_length=16)

    class Meta(object):
        app_label = 'model_tests'
        db_table = 'model_tests_testextensionmodel'


class MyTestExtensionRelatedModel(models.Model):
    """A model relating to one outside of the extension's own app.

    This is used to check that enabling an extension rebuilds the cached
    relation trees of the models its models point to.

    Version Added:
        6.1
    """

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='test_extension_related_models')

    class Meta(object):
        app_label = 'model_tests'
        db_table = 'model_tests_testextensionrelatedmodel'

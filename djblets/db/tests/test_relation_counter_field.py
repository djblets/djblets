from __future__ import unicode_literals

import gc

import django
import nose
from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete
from kgb import SpyAgency

from djblets.db.fields import RelationCounterField
from djblets.testing.testcases import TestCase, TestModelsLoaderMixin


class ReffedModel(models.Model):
    m2m_reffed_counter = RelationCounterField('m2m_reffed')
    reffed_key_counter = RelationCounterField('key_reffed')

    # These are here to ensure that RelationCounterField's smarts don't
    # over-increment/decrement other counters.
    m2m_reffed_counter_2 = RelationCounterField('m2m_reffed')
    reffed_key_counter_2 = RelationCounterField('key_reffed')

    # Here, and in following classes, we're forcing a boolean check on this
    # instance to return False so that we can make sure we're testing the
    # results correctly from weak references.
    def __nonzero__(self):
        return False


class M2MRefModel(models.Model):
    m2m = models.ManyToManyField(ReffedModel, related_name='m2m_reffed')
    counter = RelationCounterField('m2m')
    counter_2 = RelationCounterField('m2m')

    def __nonzero__(self):
        return False


class KeyRefModel(models.Model):
    key = models.ForeignKey(ReffedModel,
                            related_name='key_reffed',
                            null=True,
                            on_delete=models.CASCADE)

    def __nonzero__(self):
        return False


class BadKeyRefModel(models.Model):
    key = models.ForeignKey(ReffedModel,
                            related_name='bad_key_reffed',
                            on_delete=models.CASCADE)
    counter = RelationCounterField('key')
    counter_2 = RelationCounterField('key')

    def __nonzero__(self):
        return False


class RelationCounterFieldTests(SpyAgency, TestModelsLoaderMixin, TestCase):
    """Tests for djblets.db.fields.RelationCounterField."""
    tests_app = 'djblets.db.tests'

    # ManyToManyField.add will do 1 filter(), 1 bulk_create().
    # RelationCounterField will do 1 increment(), 1 reload() for self;
    # 1 increment() total for all objects.
    M2M_ADD_BASE_QUERY_COUNT = 2 + 3

    # RelationCounterField will do 1 reload() per item.
    M2M_ADD_LOADED_ITEM_QUERY_COUNT = 1

    # ManyToManyField.add will do 1 filter(), 1 delete()
    # RelationCounterField will do 1 decrement(), 2 update()
    M2M_REMOVE_BASE_QUERY_COUNT = 2 + 3

    # RelationCounterField will do 1 reload() per item
    M2M_REMOVE_LOADED_ITEM_QUERY_COUNT = 1

    # ManyToManyField.clear will do 2 filters(), 1 delete().
    # RelationCounterField will do 1 decrement(), 1 reload(), 1 update().
    M2M_CLEAR_BASE_QUERY_COUNT = 3 + 3

    # RelationCounterField will do 1 reload().
    M2M_CLEAR_LOADED_ITEM_QUERY_COUNT = 1

    # Django will do 1 delete().
    # RelationCounterField will do 1 decrement(), 1 reload().
    KEY_REMOVE_ITEM_QUERY_COUNT = 1 + 2

    # Django will do 1 create().
    # RelationCounterField will do 1 update().
    KEY_CREATE_UNLOADED_REL_QUERY_COUNT = 2

    # RelationCounterField will do 1 count(), 1 reload()
    REINIT_QUERY_COUNT = 2

    def setUp(self):
        super(RelationCounterFieldTests, self).setUp()

        # Make sure the state is clear due to dropped references before
        # each run.
        gc.collect()
        self.assertFalse(RelationCounterField.has_tracked_states())

    def tearDown(self):
        super(RelationCounterFieldTests, self).tearDown()

        # Make sure the state is clear due to dropped references after
        # each run.
        gc.collect()
        self.assertFalse(RelationCounterField.has_tracked_states())

    #
    # Instance tracking tests
    #

    @transaction.atomic
    def test_reused_ids_with_rollback(self):
        """Testing RelationCounterField with reused instance IDs with
        rollback
        """
        sid = transaction.savepoint()

        model = M2MRefModel.objects.create()
        added_model = ReffedModel.objects.create()
        model.m2m.add(added_model)
        self.assertEqual(model.pk, 1)
        self.assertEqual(added_model.pk, 1)
        self.assertEqual(model.counter, 1)
        self.assertEqual(model.counter_2, 1)

        # Roll back, and set up the test again.
        transaction.savepoint_rollback(sid)

        model = M2MRefModel.objects.create()
        added_model = ReffedModel.objects.create()
        model.m2m.add(added_model)
        self.assertEqual(model.pk, 1)
        self.assertEqual(added_model.pk, 1)
        self.assertEqual(model.counter, 1)
        self.assertEqual(model.counter_2, 1)

    @transaction.atomic
    def test_reused_ids_with_delete(self):
        """Testing RelationCounterField with reused instance IDs with delete"""
        if django.VERSION >= (1, 8):
            # Django 1.8 introduced the usage of transaction.atomic() in
            # the deletion code, which starts a new transaction and commits it
            # after deletion concludes. Prior versions started a transaction
            # that would only save if not already in another transaction.
            # Since 1.8+ commits the transaction, the ID ends up being reserved
            # in the database, and makes this test meaningless.
            raise nose.SkipTest('Django 1.8+ does not allow instance IDs '
                                'to be reused')

        # NOTE: The failure case would involve model.counter and
        #       model.counter_2 being 0 at the end, due to the old instance
        #       being tracked and updated.
        model = M2MRefModel()
        model.save()
        self.assertEqual(model.counter, 0)
        self.assertEqual(model.counter_2, 0)

        reffed = ReffedModel.objects.create()
        model.m2m.add(reffed)
        self.assertEqual(model.pk, 1)
        self.assertEqual(model.counter, 1)
        self.assertEqual(model.counter_2, 1)

        # Delete the main instance. The next one will have the same ID.
        model.delete()
        self.assertIsNone(model.pk)

        new_model = M2MRefModel.objects.create()
        self.assertEqual(new_model.pk, 1)
        self.assertEqual(new_model.counter, 0)
        self.assertEqual(new_model.counter_2, 0)

        # Adding a reference again should result in these counters being
        # increased, rather than the old ones.
        assert reffed.pk
        assert new_model.pk
        new_model.m2m.add(reffed)
        self.assertEqual(new_model.counter, 1)
        self.assertEqual(new_model.counter_2, 1)

        # Old model's counters aren't updated after deletion, so they'll be
        # 1. We don't want them to be 2, or it'll mean the wrong instance
        # was tracked.
        self.assertEqual(model.counter, 1)
        self.assertEqual(model.counter_2, 1)

    def test_save_calls_on_instance_first_save(self):
        """Testing RelationCounterField._on_instance_first_save called on
        first model.save()
        """
        self.spy_on(RelationCounterField._on_instance_first_save)
        save_func = RelationCounterField._on_instance_first_save

        model = M2MRefModel()
        model.save()

        self.assertTrue(save_func.last_called_with(instance=model,
                                                   created=True))
        self.assertTrue(save_func.last_returned(True))

    def test_delete_calls_on_instance_pre_delete(self):
        """Testing RelationCounterField._on_instance_pre_delete called on
        model.delete()
        """
        self.spy_on(RelationCounterField._on_instance_pre_delete)
        delete_func = RelationCounterField._on_instance_pre_delete

        model = M2MRefModel.objects.create()
        model.delete()

        self.assertTrue(delete_func.last_called_with(instance=model))
        self.assertTrue(delete_func.last_returned(True))

    def test_unsaved_and_other_double_save(self):
        """Testing RelationCounterField with an unsaved object and a double
        save on another object
        """
        # Due to a misplaced assertion, we had a bug where _on_first_save
        # was failing an assertion check when there were two instances of
        # a class, and the second one created was then saved twice. The
        # signal connection from the first stuck around and saw that
        # updated=False, which it expected would be True. However, it didn't
        # check first if it was matching the expected instance.
        self.spy_on(RelationCounterField._on_instance_first_save)
        save_func = RelationCounterField._on_instance_first_save

        model1 = M2MRefModel()
        model2 = M2MRefModel()
        self.assertIsNone(model1.pk)
        self.assertIsNone(model2.pk)

        self.assertEqual(len(save_func.calls), 0)

        # Perform the first save, which will do update=True.
        model2.save()
        self.assertEqual(len(save_func.calls), 1)
        self.assertTrue(save_func.last_called_with(instance=model2,
                                                   created=True))
        self.assertTrue(save_func.last_returned(True))

        # Perform the second save, which will do update=False.
        model2.save()
        self.assertEqual(len(save_func.calls), 2)
        self.assertTrue(save_func.last_called_with(instance=model2,
                                                   created=False))
        self.assertTrue(save_func.last_returned(False))


    #
    # Forward-relation ManyToManyField tests
    #

    def test_m2m_forward_initialize(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and initialization
        """
        with self.assertNumQueries(1):
            model = M2MRefModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)

    def test_m2m_forward_and_reinit(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and re-initialization
        """
        with self.assertNumQueries(2):
            model = M2MRefModel.objects.create()
            added_model = ReffedModel.objects.create()

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(added_model)

        with self.assertNumQueries(self.REINIT_QUERY_COUNT):
            model.counter = None
            model.reinit_counter()
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)

    def test_m2m_forward_and_create(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and creating object
        """
        with self.assertNumQueries(1):
            model = M2MRefModel.objects.create()

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_1 = model.m2m.create()
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_2 = model.m2m.create()
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

    def test_m2m_forward_and_create_with_multiple_instances(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and creating object with multiple tracked instances for ID
        """
        with self.assertNumQueries(3):
            model1 = M2MRefModel.objects.create()
            model2 = M2MRefModel.objects.get(pk=model1.pk)
            model3 = M2MRefModel.objects.get(pk=model1.pk)

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_1 = model1.m2m.create()
            self.assertEqual(model1.counter, 1)
            self.assertEqual(model1.counter_2, 1)
            self.assertEqual(model2.counter, 1)
            self.assertEqual(model2.counter_2, 1)
            self.assertEqual(model3.counter, 1)
            self.assertEqual(model3.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_2 = model1.m2m.create()
            self.assertEqual(model1.counter, 2)
            self.assertEqual(model1.counter_2, 2)
            self.assertEqual(model2.counter, 2)
            self.assertEqual(model2.counter_2, 2)
            self.assertEqual(model3.counter, 2)
            self.assertEqual(model3.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

    def test_m2m_forward_and_add(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and adding object
        """
        with self.assertNumQueries(3):
            model = M2MRefModel.objects.create()
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_1)
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_2)
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

    def test_m2m_forward_and_add_with_multiple_instances(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and adding object with multiple tracked instances for ID
        """
        with self.assertNumQueries(5):
            model1 = M2MRefModel.objects.create()
            model2 = M2MRefModel.objects.get(pk=model1.pk)
            model3 = M2MRefModel.objects.get(pk=model1.pk)
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model1.counter, 0)
            self.assertEqual(model1.counter_2, 0)
            self.assertEqual(model2.counter, 0)
            self.assertEqual(model2.counter_2, 0)
            self.assertEqual(model3.counter, 0)
            self.assertEqual(model3.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.add(rel_model_1)
            self.assertEqual(model1.counter, 1)
            self.assertEqual(model1.counter_2, 1)
            self.assertEqual(model2.counter, 1)
            self.assertEqual(model2.counter_2, 1)
            self.assertEqual(model3.counter, 1)
            self.assertEqual(model3.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.add(rel_model_2)
            self.assertEqual(model1.counter, 2)
            self.assertEqual(model1.counter, 2)
            self.assertEqual(model2.counter_2, 2)
            self.assertEqual(model2.counter_2, 2)
            self.assertEqual(model3.counter_2, 2)
            self.assertEqual(model3.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

    def test_m2m_forward_and_add_many(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and adding multiple objects
        """
        with self.assertNumQueries(3):
            model = M2MRefModel.objects.create()
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   2 * self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_1, rel_model_2)
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

    def test_m2m_forward_and_add_many_with_multiple_instances(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and adding multiple objects with multiple tracked instances for ID
        """
        with self.assertNumQueries(5):
            model1 = M2MRefModel.objects.create()
            model2 = M2MRefModel.objects.get(pk=model1.pk)
            model3 = M2MRefModel.objects.get(pk=model1.pk)
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model1.counter, 0)
            self.assertEqual(model1.counter_2, 0)
            self.assertEqual(model2.counter, 0)
            self.assertEqual(model2.counter_2, 0)
            self.assertEqual(model3.counter, 0)
            self.assertEqual(model3.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   2 * self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.add(rel_model_1, rel_model_2)
            self.assertEqual(model1.counter, 2)
            self.assertEqual(model1.counter_2, 2)
            self.assertEqual(model2.counter, 2)
            self.assertEqual(model2.counter_2, 2)
            self.assertEqual(model3.counter, 2)
            self.assertEqual(model3.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

    def test_m2m_forward_and_remove(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and removing object
        """
        with self.assertNumQueries(2):
            model = M2MRefModel.objects.create()
            rel_model = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model.m2m_reffed_counter, 0)
            self.assertEqual(rel_model.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model)
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model.m2m_reffed_counter, 1)
            self.assertEqual(rel_model.m2m_reffed_counter_2, 1)

        with self.assertNumQueries(self.M2M_REMOVE_BASE_QUERY_COUNT +
                                   self.M2M_REMOVE_LOADED_ITEM_QUERY_COUNT):
            model.m2m.remove(rel_model)
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model.m2m_reffed_counter, 0)
            self.assertEqual(rel_model.m2m_reffed_counter_2, 0)

    def test_m2m_forward_and_remove_with_multiple_instances(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and removing object with multiple tracked instances for ID
        """
        with self.assertNumQueries(4):
            model1 = M2MRefModel.objects.create()
            model2 = M2MRefModel.objects.get(pk=model1.pk)
            model3 = M2MRefModel.objects.get(pk=model1.pk)
            rel_model = ReffedModel.objects.create()
            self.assertEqual(model1.counter, 0)
            self.assertEqual(model1.counter_2, 0)
            self.assertEqual(model2.counter, 0)
            self.assertEqual(model2.counter_2, 0)
            self.assertEqual(model3.counter, 0)
            self.assertEqual(model3.counter_2, 0)
            self.assertEqual(rel_model.m2m_reffed_counter, 0)
            self.assertEqual(rel_model.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.add(rel_model)
            self.assertEqual(model1.counter, 1)
            self.assertEqual(model1.counter_2, 1)
            self.assertEqual(model2.counter, 1)
            self.assertEqual(model2.counter_2, 1)
            self.assertEqual(model3.counter, 1)
            self.assertEqual(model3.counter_2, 1)
            self.assertEqual(rel_model.m2m_reffed_counter, 1)
            self.assertEqual(rel_model.m2m_reffed_counter_2, 1)

        with self.assertNumQueries(self.M2M_REMOVE_BASE_QUERY_COUNT +
                                   self.M2M_REMOVE_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.remove(rel_model)
            self.assertEqual(model1.counter, 0)
            self.assertEqual(model1.counter_2, 0)
            self.assertEqual(model2.counter, 0)
            self.assertEqual(model2.counter_2, 0)
            self.assertEqual(model3.counter, 0)
            self.assertEqual(model3.counter_2, 0)
            self.assertEqual(rel_model.m2m_reffed_counter, 0)
            self.assertEqual(rel_model.m2m_reffed_counter_2, 0)

    def test_m2m_forward_and_clear(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and clearing all objects
        """
        with self.assertNumQueries(3):
            model = M2MRefModel.objects.create()
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_1)
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_2)
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT +
                                   2 * self.M2M_CLEAR_LOADED_ITEM_QUERY_COUNT):
            model.m2m.clear()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

    def test_m2m_forward_and_clear_with_multiple_instances(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and clearing all objects with multiple tracked instances for ID
        """
        with self.assertNumQueries(5):
            model1 = M2MRefModel.objects.create()
            model2 = M2MRefModel.objects.get(pk=model1.pk)
            model3 = M2MRefModel.objects.get(pk=model1.pk)
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model1.counter, 0)
            self.assertEqual(model1.counter_2, 0)
            self.assertEqual(model2.counter, 0)
            self.assertEqual(model2.counter_2, 0)
            self.assertEqual(model3.counter, 0)
            self.assertEqual(model3.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.add(rel_model_1)
            self.assertEqual(model1.counter, 1)
            self.assertEqual(model1.counter_2, 1)
            self.assertEqual(model2.counter, 1)
            self.assertEqual(model2.counter_2, 1)
            self.assertEqual(model3.counter, 1)
            self.assertEqual(model3.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.add(rel_model_2)
            self.assertEqual(model1.counter, 2)
            self.assertEqual(model1.counter_2, 2)
            self.assertEqual(model2.counter, 2)
            self.assertEqual(model2.counter_2, 2)
            self.assertEqual(model3.counter, 2)
            self.assertEqual(model3.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT +
                                   2 * self.M2M_CLEAR_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.clear()
            self.assertEqual(model1.counter, 0)
            self.assertEqual(model1.counter_2, 0)
            self.assertEqual(model2.counter, 0)
            self.assertEqual(model2.counter_2, 0)
            self.assertEqual(model3.counter, 0)
            self.assertEqual(model3.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

    def test_m2m_forward_and_clear_unloaded(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and clearing all unloaded objects
        """
        with self.assertNumQueries(3):
            model = M2MRefModel.objects.create()
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_1)
            self.assertEqual(model.counter, 1)
            self.assertEqual(model.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m.add(rel_model_2)
            self.assertEqual(model.counter, 2)
            self.assertEqual(model.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

        # Get rid of these for now, so that the state will drop. This will
        # ensure we're re-fetching on pre_clear.
        rel_model_id_1 = rel_model_1.pk
        rel_model_id_2 = rel_model_2.pk
        del rel_model_1
        del rel_model_2

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT):
            model.m2m.clear()
            self.assertEqual(model.counter, 0)
            self.assertEqual(model.counter_2, 0)

        with self.assertNumQueries(2):
            rel_model_1 = ReffedModel.objects.get(pk=rel_model_id_1)
            rel_model_2 = ReffedModel.objects.get(pk=rel_model_id_2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

    def test_m2m_forward_and_clear_unloaded_with_multiple_instances(self):
        """Testing RelationCounterField with forward ManyToManyField relation
        and clearing all unloaded objects with multiple tracked instances for
        ID
        """
        with self.assertNumQueries(5):
            model1 = M2MRefModel.objects.create()
            model2 = M2MRefModel.objects.get(pk=model1.pk)
            model3 = M2MRefModel.objects.get(pk=model1.pk)
            rel_model_1 = ReffedModel.objects.create()
            rel_model_2 = ReffedModel.objects.create()
            self.assertEqual(model1.counter, 0)
            self.assertEqual(model1.counter_2, 0)
            self.assertEqual(model2.counter, 0)
            self.assertEqual(model2.counter_2, 0)
            self.assertEqual(model3.counter, 0)
            self.assertEqual(model3.counter_2, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.add(rel_model_1)
            self.assertEqual(model1.counter, 1)
            self.assertEqual(model1.counter_2, 1)
            self.assertEqual(model2.counter, 1)
            self.assertEqual(model2.counter_2, 1)
            self.assertEqual(model3.counter, 1)
            self.assertEqual(model3.counter_2, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m.add(rel_model_2)
            self.assertEqual(model1.counter, 2)
            self.assertEqual(model1.counter_2, 2)
            self.assertEqual(model2.counter, 2)
            self.assertEqual(model2.counter_2, 2)
            self.assertEqual(model3.counter, 2)
            self.assertEqual(model3.counter_2, 2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 1)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 1)

        # Get rid of these for now, so that the state will drop. This will
        # ensure we're re-fetching on pre_clear.
        rel_model_id_1 = rel_model_1.pk
        rel_model_id_2 = rel_model_2.pk
        del rel_model_1
        del rel_model_2

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT):
            model1.m2m.clear()
            self.assertEqual(model1.counter, 0)
            self.assertEqual(model1.counter_2, 0)
            self.assertEqual(model2.counter, 0)
            self.assertEqual(model2.counter_2, 0)
            self.assertEqual(model3.counter, 0)
            self.assertEqual(model3.counter_2, 0)

        with self.assertNumQueries(2):
            rel_model_1 = ReffedModel.objects.get(pk=rel_model_id_1)
            rel_model_2 = ReffedModel.objects.get(pk=rel_model_id_2)
            self.assertEqual(rel_model_1.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_1.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter, 0)
            self.assertEqual(rel_model_2.m2m_reffed_counter_2, 0)

    #
    # Reverse-relation ManyToManyField tests
    #

    def test_m2m_reverse_initialize(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and initialization
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)

    def test_m2m_reverse_and_reinit(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and re-initialization
        """
        with self.assertNumQueries(2):
            model = ReffedModel.objects.create()
            rel_model = M2MRefModel.objects.create()

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model)

        with self.assertNumQueries(self.REINIT_QUERY_COUNT):
            model.m2m_reffed_counter = None
            model.reinit_m2m_reffed_counter()
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)

    def test_m2m_reverse_and_create(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and creating object
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_1 = model.m2m_reffed.create()
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_2 = model.m2m_reffed.create()
            self.assertEqual(model.m2m_reffed_counter, 2)
            self.assertEqual(model.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

    def test_m2m_reverse_and_create_with_multiple_instances(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and creating object with multiple tracked instances for ID
        """
        with self.assertNumQueries(3):
            model1 = ReffedModel.objects.create()
            model2 = ReffedModel.objects.get(pk=model1.pk)
            model3 = ReffedModel.objects.get(pk=model1.pk)

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_1 = model1.m2m_reffed.create()
            self.assertEqual(model1.m2m_reffed_counter, 1)
            self.assertEqual(model1.m2m_reffed_counter_2, 1)
            self.assertEqual(model2.m2m_reffed_counter, 1)
            self.assertEqual(model2.m2m_reffed_counter_2, 1)
            self.assertEqual(model3.m2m_reffed_counter, 1)
            self.assertEqual(model3.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)

        with self.assertNumQueries(1 +
                                   self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            rel_model_2 = model1.m2m_reffed.create()
            self.assertEqual(model1.m2m_reffed_counter, 2)
            self.assertEqual(model1.m2m_reffed_counter_2, 2)
            self.assertEqual(model2.m2m_reffed_counter, 2)
            self.assertEqual(model2.m2m_reffed_counter_2, 2)
            self.assertEqual(model3.m2m_reffed_counter, 2)
            self.assertEqual(model3.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

    def test_m2m_reverse_and_add(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and adding object
        """
        with self.assertNumQueries(3):
            model = ReffedModel.objects.create()
            rel_model_1 = M2MRefModel.objects.create()
            rel_model_2 = M2MRefModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_1)
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_2)
            self.assertEqual(model.m2m_reffed_counter, 2)
            self.assertEqual(model.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

    def test_m2m_reverse_and_add_with_multiple_instances(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and adding object with multiple tracked instances for ID
        """
        with self.assertNumQueries(5):
            model1 = ReffedModel.objects.create()
            model2 = ReffedModel.objects.get(pk=model1.pk)
            model3 = ReffedModel.objects.get(pk=model2.pk)
            rel_model_1 = M2MRefModel.objects.create()
            rel_model_2 = M2MRefModel.objects.create()
            self.assertEqual(model1.m2m_reffed_counter, 0)
            self.assertEqual(model1.m2m_reffed_counter_2, 0)
            self.assertEqual(model2.m2m_reffed_counter, 0)
            self.assertEqual(model2.m2m_reffed_counter_2, 0)
            self.assertEqual(model3.m2m_reffed_counter, 0)
            self.assertEqual(model3.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m_reffed.add(rel_model_1)
            self.assertEqual(model1.m2m_reffed_counter, 1)
            self.assertEqual(model1.m2m_reffed_counter_2, 1)
            self.assertEqual(model2.m2m_reffed_counter, 1)
            self.assertEqual(model2.m2m_reffed_counter_2, 1)
            self.assertEqual(model3.m2m_reffed_counter, 1)
            self.assertEqual(model3.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m_reffed.add(rel_model_2)
            self.assertEqual(model1.m2m_reffed_counter, 2)
            self.assertEqual(model1.m2m_reffed_counter_2, 2)
            self.assertEqual(model2.m2m_reffed_counter, 2)
            self.assertEqual(model2.m2m_reffed_counter_2, 2)
            self.assertEqual(model3.m2m_reffed_counter, 2)
            self.assertEqual(model3.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

    def test_m2m_reverse_and_remove(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and removing object
        """
        with self.assertNumQueries(2):
            model = ReffedModel.objects.create()
            rel_model = M2MRefModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model.counter, 0)
            self.assertEqual(rel_model.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model)
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model.counter, 1)
            self.assertEqual(rel_model.counter_2, 1)

        with self.assertNumQueries(self.M2M_REMOVE_BASE_QUERY_COUNT +
                                   self.M2M_REMOVE_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.remove(rel_model)
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model.counter, 0)
            self.assertEqual(rel_model.counter_2, 0)

    def test_m2m_reverse_and_remove_with_multiple_instances(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and removing object with multiple tracked instances
        """
        with self.assertNumQueries(4):
            model1 = ReffedModel.objects.create()
            model2 = ReffedModel.objects.get(pk=model1.pk)
            model3 = ReffedModel.objects.get(pk=model1.pk)
            rel_model = M2MRefModel.objects.create()
            self.assertEqual(model1.m2m_reffed_counter, 0)
            self.assertEqual(model1.m2m_reffed_counter_2, 0)
            self.assertEqual(model2.m2m_reffed_counter, 0)
            self.assertEqual(model2.m2m_reffed_counter_2, 0)
            self.assertEqual(model3.m2m_reffed_counter, 0)
            self.assertEqual(model3.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model.counter, 0)
            self.assertEqual(rel_model.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m_reffed.add(rel_model)
            self.assertEqual(model1.m2m_reffed_counter, 1)
            self.assertEqual(model1.m2m_reffed_counter_2, 1)
            self.assertEqual(model2.m2m_reffed_counter, 1)
            self.assertEqual(model2.m2m_reffed_counter, 1)
            self.assertEqual(model3.m2m_reffed_counter_2, 1)
            self.assertEqual(model3.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model.counter, 1)
            self.assertEqual(rel_model.counter_2, 1)

        with self.assertNumQueries(self.M2M_REMOVE_BASE_QUERY_COUNT +
                                   self.M2M_REMOVE_LOADED_ITEM_QUERY_COUNT):
            model1.m2m_reffed.remove(rel_model)
            self.assertEqual(model1.m2m_reffed_counter, 0)
            self.assertEqual(model1.m2m_reffed_counter_2, 0)
            self.assertEqual(model2.m2m_reffed_counter, 0)
            self.assertEqual(model2.m2m_reffed_counter_2, 0)
            self.assertEqual(model3.m2m_reffed_counter, 0)
            self.assertEqual(model3.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model.counter, 0)
            self.assertEqual(rel_model.counter_2, 0)

    def test_m2m_reverse_and_clear(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and clearing all objects
        """
        with self.assertNumQueries(3):
            model = ReffedModel.objects.create()
            rel_model_1 = M2MRefModel.objects.create()
            rel_model_2 = M2MRefModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_1)
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_2)
            self.assertEqual(model.m2m_reffed_counter, 2)
            self.assertEqual(model.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT +
                                   2 * self.M2M_CLEAR_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.clear()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

    def test_m2m_reverse_and_clear_with_multiple_instances(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and clearing all objects with multiple tracked instances for ID
        """
        with self.assertNumQueries(5):
            model1 = ReffedModel.objects.create()
            model2 = ReffedModel.objects.get(pk=model1.pk)
            model3 = ReffedModel.objects.get(pk=model1.pk)
            rel_model_1 = M2MRefModel.objects.create()
            rel_model_2 = M2MRefModel.objects.create()
            self.assertEqual(model1.m2m_reffed_counter, 0)
            self.assertEqual(model1.m2m_reffed_counter_2, 0)
            self.assertEqual(model2.m2m_reffed_counter, 0)
            self.assertEqual(model2.m2m_reffed_counter_2, 0)
            self.assertEqual(model3.m2m_reffed_counter, 0)
            self.assertEqual(model3.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m_reffed.add(rel_model_1)
            self.assertEqual(model1.m2m_reffed_counter, 1)
            self.assertEqual(model1.m2m_reffed_counter_2, 1)
            self.assertEqual(model2.m2m_reffed_counter, 1)
            self.assertEqual(model2.m2m_reffed_counter_2, 1)
            self.assertEqual(model3.m2m_reffed_counter, 1)
            self.assertEqual(model3.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m_reffed.add(rel_model_2)
            self.assertEqual(model1.m2m_reffed_counter, 2)
            self.assertEqual(model1.m2m_reffed_counter_2, 2)
            self.assertEqual(model2.m2m_reffed_counter, 2)
            self.assertEqual(model2.m2m_reffed_counter_2, 2)
            self.assertEqual(model3.m2m_reffed_counter, 2)
            self.assertEqual(model3.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT +
                                   2 * self.M2M_CLEAR_LOADED_ITEM_QUERY_COUNT):
            model1.m2m_reffed.clear()
            self.assertEqual(model1.m2m_reffed_counter, 0)
            self.assertEqual(model1.m2m_reffed_counter_2, 0)
            self.assertEqual(model2.m2m_reffed_counter, 0)
            self.assertEqual(model2.m2m_reffed_counter_2, 0)
            self.assertEqual(model3.m2m_reffed_counter, 0)
            self.assertEqual(model3.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

    def test_m2m_reverse_and_clear_unloaded(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and clearing all unloaded objects
        """
        with self.assertNumQueries(3):
            model = ReffedModel.objects.create()
            rel_model_1 = M2MRefModel.objects.create()
            rel_model_2 = M2MRefModel.objects.create()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_1)
            self.assertEqual(model.m2m_reffed_counter, 1)
            self.assertEqual(model.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model.m2m_reffed.add(rel_model_2)
            self.assertEqual(model.m2m_reffed_counter, 2)
            self.assertEqual(model.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

        # Get rid of these for now, so that the state will drop. This will
        # ensure we're re-fetching on pre_clear.
        rel_model_id_1 = rel_model_1.pk
        rel_model_id_2 = rel_model_2.pk
        del rel_model_1
        del rel_model_2

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT):
            model.m2m_reffed.clear()
            self.assertEqual(model.m2m_reffed_counter, 0)
            self.assertEqual(model.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(2):
            rel_model_1 = M2MRefModel.objects.get(pk=rel_model_id_1)
            rel_model_2 = M2MRefModel.objects.get(pk=rel_model_id_2)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

    def test_m2m_reverse_and_clear_unloaded_with_multiple_instances(self):
        """Testing RelationCounterField with reverse ManyToManyField relation
        and clearing all unloaded objects with multiple tracked instances for
        ID
        """
        with self.assertNumQueries(5):
            model1 = ReffedModel.objects.create()
            model2 = ReffedModel.objects.get(pk=model1.pk)
            model3 = ReffedModel.objects.get(pk=model1.pk)
            rel_model_1 = M2MRefModel.objects.create()
            rel_model_2 = M2MRefModel.objects.create()
            self.assertEqual(model1.m2m_reffed_counter, 0)
            self.assertEqual(model1.m2m_reffed_counter_2, 0)
            self.assertEqual(model2.m2m_reffed_counter, 0)
            self.assertEqual(model2.m2m_reffed_counter_2, 0)
            self.assertEqual(model3.m2m_reffed_counter, 0)
            self.assertEqual(model3.m2m_reffed_counter_2, 0)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m_reffed.add(rel_model_1)
            self.assertEqual(model1.m2m_reffed_counter, 1)
            self.assertEqual(model1.m2m_reffed_counter_2, 1)
            self.assertEqual(model2.m2m_reffed_counter, 1)
            self.assertEqual(model2.m2m_reffed_counter_2, 1)
            self.assertEqual(model3.m2m_reffed_counter, 1)
            self.assertEqual(model3.m2m_reffed_counter_2, 1)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

        with self.assertNumQueries(self.M2M_ADD_BASE_QUERY_COUNT +
                                   self.M2M_ADD_LOADED_ITEM_QUERY_COUNT):
            model1.m2m_reffed.add(rel_model_2)
            self.assertEqual(model1.m2m_reffed_counter, 2)
            self.assertEqual(model1.m2m_reffed_counter_2, 2)
            self.assertEqual(model2.m2m_reffed_counter, 2)
            self.assertEqual(model2.m2m_reffed_counter_2, 2)
            self.assertEqual(model3.m2m_reffed_counter, 2)
            self.assertEqual(model3.m2m_reffed_counter_2, 2)
            self.assertEqual(rel_model_1.counter, 1)
            self.assertEqual(rel_model_1.counter_2, 1)
            self.assertEqual(rel_model_2.counter, 1)
            self.assertEqual(rel_model_2.counter_2, 1)

        # Get rid of these for now, so that the state will drop. This will
        # ensure we're re-fetching on pre_clear.
        rel_model_id_1 = rel_model_1.pk
        rel_model_id_2 = rel_model_2.pk
        del rel_model_1
        del rel_model_2

        with self.assertNumQueries(self.M2M_CLEAR_BASE_QUERY_COUNT):
            model1.m2m_reffed.clear()
            self.assertEqual(model1.m2m_reffed_counter, 0)
            self.assertEqual(model1.m2m_reffed_counter_2, 0)
            self.assertEqual(model2.m2m_reffed_counter, 0)
            self.assertEqual(model2.m2m_reffed_counter_2, 0)
            self.assertEqual(model3.m2m_reffed_counter, 0)
            self.assertEqual(model3.m2m_reffed_counter_2, 0)

        with self.assertNumQueries(2):
            rel_model_1 = M2MRefModel.objects.get(pk=rel_model_id_1)
            rel_model_2 = M2MRefModel.objects.get(pk=rel_model_id_2)
            self.assertEqual(rel_model_1.counter, 0)
            self.assertEqual(rel_model_1.counter_2, 0)
            self.assertEqual(rel_model_2.counter, 0)
            self.assertEqual(rel_model_2.counter_2, 0)

    #
    # Forward-relation ForeignKey tests
    #

    def test_fkey_forward_initialize(self):
        """Testing RelationCounterField with forward ForeignKey relation
        and initialization disallowed
        """
        with self.assertNumQueries(0):
            self.assertRaisesMessage(
                ValueError,
                "RelationCounterField cannot work with the forward "
                "end of a ForeignKey ('key')",
                lambda: BadKeyRefModel())

    #
    # Reverse-relation ForeignKey tests
    #

    def test_fkey_reverse_initialize(self):
        """Testing RelationCounterField with reverse ForeignKey relation
        and initialization
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

    def test_fkey_reverse_and_reinit(self):
        """Testing RelationCounterField with reverse ForeignKey relation
        and re-initialization
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            KeyRefModel.objects.create(key=model)

        with self.assertNumQueries(self.REINIT_QUERY_COUNT):
            model.reffed_key_counter = None
            model.reinit_reffed_key_counter()
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

    def test_fkey_reverse_and_add(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        adding object
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 2)
            self.assertEqual(model.reffed_key_counter_2, 2)

    def test_fkey_reverse_and_add_with_multiple_instances(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        adding object with multiple tracked instances for ID
        """
        with self.assertNumQueries(3):
            model1 = ReffedModel.objects.create()
            model2 = ReffedModel.objects.get(pk=model1.pk)
            model3 = ReffedModel.objects.get(pk=model1.pk)
            self.assertEqual(model1.reffed_key_counter, 0)
            self.assertEqual(model1.reffed_key_counter_2, 0)
            self.assertEqual(model2.reffed_key_counter, 0)
            self.assertEqual(model2.reffed_key_counter_2, 0)
            self.assertEqual(model3.reffed_key_counter, 0)
            self.assertEqual(model3.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            KeyRefModel.objects.create(key=model1)
            self.assertEqual(model1.reffed_key_counter, 1)
            self.assertEqual(model1.reffed_key_counter_2, 1)
            self.assertEqual(model2.reffed_key_counter, 1)
            self.assertEqual(model2.reffed_key_counter_2, 1)
            self.assertEqual(model3.reffed_key_counter, 1)
            self.assertEqual(model3.reffed_key_counter_2, 1)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            KeyRefModel.objects.create(key=model1)
            self.assertEqual(model1.reffed_key_counter, 2)
            self.assertEqual(model1.reffed_key_counter_2, 2)
            self.assertEqual(model2.reffed_key_counter, 2)
            self.assertEqual(model2.reffed_key_counter_2, 2)
            self.assertEqual(model3.reffed_key_counter, 2)
            self.assertEqual(model3.reffed_key_counter_2, 2)

    def test_fkey_reverse_and_add_unloaded_by_id(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        adding unloaded object by ID
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        model_id = model.pk
        del model

        with self.assertNumQueries(self.KEY_CREATE_UNLOADED_REL_QUERY_COUNT):
            KeyRefModel.objects.create(key_id=model_id)

        with self.assertNumQueries(1):
            model = ReffedModel.objects.get(pk=model_id)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

    def test_fkey_reverse_and_delete(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        deleting object
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        with self.assertNumQueries(self.KEY_REMOVE_ITEM_QUERY_COUNT):
            rel_model.delete()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

    def test_fkey_reverse_and_delete_with_multiple_instances(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        deleting object with multiple tracked instances for ID
        """
        with self.assertNumQueries(3):
            model1 = ReffedModel.objects.create()
            model2 = ReffedModel.objects.get(pk=model1.pk)
            model3 = ReffedModel.objects.get(pk=model1.pk)
            self.assertEqual(model1.reffed_key_counter, 0)
            self.assertEqual(model1.reffed_key_counter_2, 0)
            self.assertEqual(model2.reffed_key_counter, 0)
            self.assertEqual(model2.reffed_key_counter_2, 0)
            self.assertEqual(model3.reffed_key_counter, 0)
            self.assertEqual(model3.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model1)
            self.assertEqual(model1.reffed_key_counter, 1)
            self.assertEqual(model1.reffed_key_counter_2, 1)
            self.assertEqual(model2.reffed_key_counter, 1)
            self.assertEqual(model2.reffed_key_counter_2, 1)
            self.assertEqual(model3.reffed_key_counter, 1)
            self.assertEqual(model3.reffed_key_counter_2, 1)

        with self.assertNumQueries(self.KEY_REMOVE_ITEM_QUERY_COUNT):
            rel_model.delete()
            self.assertEqual(model1.reffed_key_counter, 0)
            self.assertEqual(model1.reffed_key_counter_2, 0)
            self.assertEqual(model2.reffed_key_counter, 0)
            self.assertEqual(model2.reffed_key_counter_2, 0)
            self.assertEqual(model3.reffed_key_counter, 0)
            self.assertEqual(model3.reffed_key_counter_2, 0)

    def test_fkey_reverse_and_save_existing(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        saving existing object doesn't modify counts
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        with self.assertNumQueries(1):
            rel_model.save()
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

    def test_fkey_reverse_and_save_existing_with_multiple_instances(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        saving existing object doesn't modify counts with multiple tracked
        instances for ID
        """
        with self.assertNumQueries(3):
            model1 = ReffedModel.objects.create()
            model2 = ReffedModel.objects.get(pk=model1.pk)
            model3 = ReffedModel.objects.get(pk=model1.pk)
            self.assertEqual(model1.reffed_key_counter, 0)
            self.assertEqual(model1.reffed_key_counter_2, 0)
            self.assertEqual(model2.reffed_key_counter, 0)
            self.assertEqual(model2.reffed_key_counter_2, 0)
            self.assertEqual(model3.reffed_key_counter, 0)
            self.assertEqual(model3.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model1)
            self.assertEqual(model1.reffed_key_counter, 1)
            self.assertEqual(model1.reffed_key_counter_2, 1)
            self.assertEqual(model2.reffed_key_counter, 1)
            self.assertEqual(model2.reffed_key_counter_2, 1)
            self.assertEqual(model3.reffed_key_counter, 1)
            self.assertEqual(model3.reffed_key_counter_2, 1)

        with self.assertNumQueries(1):
            rel_model.save()
            self.assertEqual(model1.reffed_key_counter, 1)
            self.assertEqual(model1.reffed_key_counter_2, 1)
            self.assertEqual(model2.reffed_key_counter, 1)
            self.assertEqual(model2.reffed_key_counter_2, 1)
            self.assertEqual(model3.reffed_key_counter, 1)
            self.assertEqual(model3.reffed_key_counter_2, 1)

    def test_fkey_reverse_delete_unloaded(self):
        """Testing RelationCounterField with reverse ForeignKey relation
        and deleting unloaded object
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        model_id = model.pk
        del model

        with self.assertNumQueries(self.KEY_REMOVE_ITEM_QUERY_COUNT):
            rel_model.delete()

        with self.assertNumQueries(1):
            model = ReffedModel.objects.get(pk=model_id)
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

    def test_fkey_reverse_and_delete_with_all_unloaded(self):
        """Testing RelationCounterField with reverse ForeignKey relation and
        deleting object with all instances unloaded
        """
        with self.assertNumQueries(1):
            model = ReffedModel.objects.create()
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

        with self.assertNumQueries(1 + self.REINIT_QUERY_COUNT):
            rel_model = KeyRefModel.objects.create(key=model)
            self.assertEqual(model.reffed_key_counter, 1)
            self.assertEqual(model.reffed_key_counter_2, 1)

        model_id = model.pk
        del model
        del rel_model

        with self.assertNumQueries(self.KEY_REMOVE_ITEM_QUERY_COUNT):
            KeyRefModel.objects.all().delete()

        with self.assertNumQueries(1):
            model = ReffedModel.objects.get(pk=model_id)
            self.assertEqual(model.reffed_key_counter, 0)
            self.assertEqual(model.reffed_key_counter_2, 0)

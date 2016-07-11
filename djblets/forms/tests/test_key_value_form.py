from __future__ import unicode_literals

from django import forms

from djblets.forms.forms import KeyValueForm
from djblets.testing.testcases import TestCase


class DummyForm(KeyValueForm):
    char_field = forms.CharField(initial='default', required=False)
    bool_field = forms.BooleanField(initial=True, required=False)

    def __init__(self, *args, **kwargs):
        self.saved = False

        super(DummyForm, self).__init__(*args, **kwargs)

    def create_instance(self):
        return {}

    def save_instance(self):
        self.saved = True


class KeyValueFormTests(TestCase):
    """Unit tests for djblets.forms.forms.KeyValueForm."""

    def test_load_without_instance(self):
        """Testing KeyValueForm load without instance"""
        form = DummyForm()

        self.assertEqual(form.fields['char_field'].initial, 'default')
        self.assertTrue(form.fields['bool_field'].initial)

    def test_load_with_instance(self):
        """Testing KeyValueForm.load with instance"""
        form = DummyForm(instance={
            'char_field': 'new value',
            'bool_field': False,
        })

        self.assertEqual(form.fields['char_field'].initial, 'new value')
        self.assertFalse(form.fields['bool_field'].initial)

    def test_load_with_load_blacklist(self):
        """Testing KeyValueForm.load with Meta.load_blacklist"""
        class LoadBlacklistForm(DummyForm):
            class Meta:
                load_blacklist = ('char_field',)
                save_blacklist = ('bool_field',)

        form = LoadBlacklistForm(instance={
            'char_field': 'new value',
            'bool_field': False,
        })

        self.assertEqual(form.fields['char_field'].initial, 'default')
        self.assertFalse(form.fields['bool_field'].initial)

    def test_load_with_save_blacklist(self):
        """Testing KeyValueForm.load with Meta.save_blacklist only"""
        class LoadBlacklistForm(DummyForm):
            class Meta:
                save_blacklist = ('char_field',)

        form = LoadBlacklistForm(instance={
            'char_field': 'new value',
            'bool_field': False,
        })

        self.assertEqual(form.fields['char_field'].initial, 'default')
        self.assertFalse(form.fields['bool_field'].initial)

    def test_load_with_disabled_fields(self):
        """Testing KeyValueForm.load with disabled_fields"""
        class DisabledFieldsForm(DummyForm):
            def load(self):
                self.disabled_fields['char_field'] = True

                super(DisabledFieldsForm, self).load()

            class Meta:
                save_blacklist = ('char_field',)

        form = DisabledFieldsForm(instance={
            'char_field': 'new value',
            'bool_field': False,
        })

        self.assertIn('disabled', form.fields['char_field'].widget.attrs)
        self.assertEqual(form.fields['char_field'].widget.attrs['disabled'],
                         'disabled')
        self.assertNotIn('disabled', form.fields['bool_field'].widget.attrs)

    def test_load_with_custom_deserialized_field(self):
        """Testing KeyValueForm.load with custom deserializer for field"""
        class DeserializerForm(DummyForm):
            custom = forms.CharField()

            def deserialize_custom_field(self, value):
                return value['value']

        form = DeserializerForm(instance={
            'custom': {
                'is_custom': True,
                'value': 'my value',
            },
        })

        self.assertEqual(form.fields['custom'].initial, 'my value')

    def test_save_without_instance(self):
        """Testing KeyValueForm.save without existing instance"""
        form = DummyForm(data={
            'char_field': 'new value',
            'bool_field': False,
        })

        self.assertTrue(form.is_valid())
        result = form.save()

        self.assertEqual(
            result,
            {
                'char_field': 'new value',
                'bool_field': False,
            })
        self.assertTrue(form.saved)

    def test_save_with_instance(self):
        """Testing KeyValueForm.save with existing instance"""
        instance = {
            'char_field': 'orig value',
            'bool_field': False,
        }
        form = DummyForm(
            instance=instance,
            data={
                'char_field': 'new value',
                'bool_field': False,
            })

        self.assertTrue(form.is_valid())
        result = form.save()

        self.assertEqual(
            result,
            {
                'char_field': 'new value',
                'bool_field': False,
            })
        self.assertTrue(form.saved)
        self.assertTrue(instance is result)

    def test_save_with_instance_no_commit(self):
        """Testing KeyValueForm.save with existing instance and with
        commit=False
        """
        instance = {
            'char_field': 'orig value',
            'bool_field': False,
        }
        form = DummyForm(
            instance=instance,
            data={
                'char_field': 'new value',
                'bool_field': False,
            })

        self.assertTrue(form.is_valid())
        result = form.save(commit=False)

        self.assertEqual(
            result,
            {
                'char_field': 'new value',
                'bool_field': False,
            })
        self.assertFalse(form.saved)
        self.assertTrue(instance is result)

    def test_save_with_save_blacklist(self):
        """Testing KeyValueForm.save with Meta.save_blacklist"""
        class SaveBlacklistForm(DummyForm):
            class Meta:
                save_blacklist = ('char_field',)

        instance = {
            'char_field': 'orig value',
            'bool_field': False,
        }
        form = SaveBlacklistForm(
            instance=instance,
            data={
                'char_field': 'new value',
                'bool_field': True,
            })

        self.assertTrue(form.is_valid())
        result = form.save()

        self.assertEqual(
            result,
            {
                'char_field': 'orig value',
                'bool_field': True,
            })
        self.assertTrue(instance is result)

    def test_save_with_extra_save_blacklist(self):
        """Testing KeyValueForm.save with Meta.extra_save_blacklist"""
        class SaveBlacklistForm(DummyForm):
            class Meta:
                save_blacklist = ('char_field',)

        instance = {
            'char_field': 'orig value',
            'bool_field': False,
        }
        form = SaveBlacklistForm(
            instance=instance,
            data={
                'char_field': 'new value',
                'bool_field': True,
            })

        self.assertTrue(form.is_valid())
        result = form.save(extra_save_blacklist=('bool_field',))

        self.assertEqual(
            result,
            {
                'char_field': 'orig value',
                'bool_field': False,
            })
        self.assertTrue(instance is result)

    def test_save_with_custom_serialized_field(self):
        """Testing KeyValueForm.save with custom serializer for field"""
        class SerializerForm(DummyForm):
            custom = forms.CharField()

            def serialize_custom_field(self, value):
                return {
                    'is_custom': True,
                    'value': value,
                }

        instance = {
            'custom': {
                'is_custom': True,
                'value': 'orig value',
            },
        }

        form = SerializerForm(
            instance=instance,
            data={
                'custom': 'new value',
            })

        self.assertTrue(form.is_valid())
        result = form.save()

        self.assertTrue(instance is result)
        self.assertEqual(
            result['custom'],
            {
                'is_custom': True,
                'value': 'new value',
            })

"""Unit tests for djblets.webapi.resources.mixins.forms.UpdateFormMixin."""

from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from kgb import SpyAgency

from djblets.testing.testcases import TestCase
from djblets.webapi.errors import INVALID_FORM_DATA
from djblets.webapi.resources.mixins.forms import UpdateFormMixin


class MyForm(forms.ModelForm):
    first_name = forms.CharField(initial='initial-first-name',
                                 required=False)

    def __init__(self, *args, **kwargs):
        self.custom = kwargs.pop('custom', False)

        super(MyForm, self).__init__(*args, **kwargs)

    class Meta:
        model = User
        fields = ['username', 'password', 'first_name', 'last_name']


class UpdateFormMixinTests(SpyAgency, TestCase):
    """Unit tests for djblets.webapi.resources.mixins.forms.UpdateFormMixin."""

    def setUp(self):
        super(UpdateFormMixinTests, self).setUp()

        self.mixin = UpdateFormMixin()
        self.mixin.form_class = MyForm
        self.mixin.item_result_key = 'user'

    def test_build_form_errors_with_form(self):
        """Testing UpdateFormMixin.build_form_errors with form"""
        form = MyForm(data={})

        self.assertEqual(
            self.mixin.build_form_errors(form=form),
            {
                'username': ['This field is required.'],
                'password': ['This field is required.'],
            })

    def test_build_form_errors_with_validation_error_dict(self):
        """Testing UpdateFormMixin.build_form_errors with ValidationError
        using dictionary
        """
        errors = ValidationError({
            'field1': ['This field is required.'],
            'field2': ['This is not a valid choice.'],
        })

        self.assertEqual(
            self.mixin.build_form_errors(errors=errors),
            {
                'field1': ['This field is required.'],
                'field2': ['This is not a valid choice.'],
            })

    def test_build_form_errors_with_validation_error_list(self):
        """Testing UpdateFormMixin.build_form_errors with ValidationError
        using list
        """
        errors = ValidationError([
            'Oh no.',
            ValidationError('Everything went wrong.'),
        ])

        self.assertEqual(
            self.mixin.build_form_errors(errors=errors),
            {
                '__all__': ['Oh no.', 'Everything went wrong.'],
            })

    def test_build_form_success_response_with_is_created_true(self):
        """Testing UpdateFormMixin.build_form_success_response with
        is_created=True
        """
        form = MyForm()
        user = User(username='my-user')
        response = self.mixin.build_form_success_response(form=form,
                                                          instance=user,
                                                          is_created=True)

        self.assertEqual(
            response,
            (201, {
                'user': user,
            }))

    def test_build_form_success_response_with_is_created_false(self):
        """Testing UpdateFormMixin.build_form_success_response with
        is_created=False
        """
        form = MyForm()
        user = User(username='my-user')
        response = self.mixin.build_form_success_response(form=form,
                                                          instance=user,
                                                          is_created=False)

        self.assertEqual(
            response,
            (200, {
                'user': user,
            }))

    def test_build_form_error_response_with_form(self):
        """Testing UpdateFormMixin.build_form_error_response with form"""
        form = MyForm(data={})
        response = self.mixin.build_form_error_response(form=form)

        self.assertEqual(
            response,
            (INVALID_FORM_DATA, {
                'fields': {
                    'username': ['This field is required.'],
                    'password': ['This field is required.'],
                },
            }))

    def test_build_form_error_response_with_validation_error(self):
        """Testing UpdateFormMixin.build_form_error_response with
        ValidationError
        """
        errors = ValidationError({
            'field1': ['This field is required.'],
            'field2': ['This is not a valid choice.'],
        })

        response = self.mixin.build_form_error_response(errors=errors)

        self.assertEqual(
            response,
            (INVALID_FORM_DATA, {
                'fields': {
                    'field1': ['This field is required.'],
                    'field2': ['This is not a valid choice.'],
                },
            }))

    def test_create_form(self):
        """Testing UpdateFormMixin.create_form"""
        form = self.mixin.create_form(
            data={
                'username': 'test-user',
                'password': 'test-pass',
            },
            request=None,
            form_kwargs={
                'custom': True,
            })

        self.assertTrue(form.custom)
        self.assertEqual(form.data['username'], 'test-user')
        self.assertEqual(form.data['password'], 'test-pass')
        self.assertEqual(form.data['first_name'], 'initial-first-name')

    def test_create_form_with_instance(self):
        """Testing UpdateFormMixin.create_form with instance"""
        user = User(username='test-user',
                    password='test-pass',
                    first_name='test-first-name',
                    last_name='test-last-name')

        form = self.mixin.create_form(
            data={
                'username': 'new-test-user',
                'last_name': 'new-last-name',
            },
            request=None,
            instance=user,
            form_kwargs={
                'custom': True,
            })

        self.assertTrue(form.custom)
        self.assertEqual(form.data['username'], 'new-test-user')
        self.assertEqual(form.data['password'], 'test-pass')
        self.assertEqual(form.data['first_name'], 'test-first-name')
        self.assertEqual(form.data['last_name'], 'new-last-name')

    def test_create_form_with_parse_field(self):
        """Testing UpdateFormMixin.create_form with parse_*_field method"""
        self.mixin.parse_username_field = \
            lambda value, my_state, **kwargs: 'test-%s-%s' % (value, my_state)

        form = self.mixin.create_form(
            data={
                'username': 'user',
                'password': 'test-pass',
            },
            request=None,
            form_kwargs={
                'custom': True,
            },
            my_state=123)

        self.assertTrue(form.custom)
        self.assertEqual(form.data['username'], 'test-user-123')
        self.assertEqual(form.data['password'], 'test-pass')

    def test_create_form_with_parse_field_raising_error(self):
        """Testing UpdateFormMixin.create_form with parse_*_field method
        raising ValidationError
        """
        def _parse_field(value, **kwargs):
            raise ValidationError('This field is just bad.')

        self.mixin.parse_username_field = _parse_field
        self.mixin.parse_password_field = _parse_field

        with self.assertRaises(ValidationError) as ctx:
            self.mixin.create_form(
                data={
                    'username': 'user',
                    'password': 'pass',
                },
                request=None,
                form_kwargs={
                    'custom': True,
                })

        self.assertEqual(ctx.exception.message_dict, {
            'username': ['This field is just bad.'],
            'password': ['This field is just bad.'],
        })

    def test_handle_form_request(self):
        """Testing UpdateFormMixin.handle_form_request"""
        self.spy_on(MyForm.save)

        response = self.mixin.handle_form_request(
            data={
                'username': 'test-user',
                'password': 'test-pass',
            },
            request=None,
            form_kwargs={
                'custom': True,
            },
            save_kwargs={
                'commit': False,
            },
            my_state=123)

        user = MyForm.save.last_call.return_value
        self.assertIsNone(user.pk)
        self.assertEqual(user.username, 'test-user')

        self.assertEqual(
            response,
            (201, {
                'user': user,
            }))

    def test_handle_form_request_with_instance(self):
        """Testing UpdateFormMixin.handle_form_request with instance"""
        user = User(username='test-user',
                    password='test-pass')

        response = self.mixin.handle_form_request(
            data={
                'username': 'new-user',
                'first_name': 'new-first-name',
                'last_name': 'new-last-name',
            },
            request=None,
            instance=user,
            form_kwargs={
                'custom': True,
            },
            my_state=123)

        user = User.objects.get()
        self.assertEqual(user.username, 'new-user')
        self.assertEqual(user.first_name, 'new-first-name')
        self.assertEqual(user.last_name, 'new-last-name')

        self.assertEqual(
            response,
            (200, {
                'user': user,
            }))

    def test_handle_form_request_with_error(self):
        """Testing UpdateFormMixin.handle_form_request with error"""
        response = self.mixin.handle_form_request(
            data={},
            request=None,
            form_kwargs={
                'custom': True,
            },
            my_state=123)

        self.assertEqual(
            response,
            (INVALID_FORM_DATA, {
                'fields': {
                    'username': ['This field is required.'],
                    'password': ['This field is required.'],
                },
            }))

    def test_handle_form_request_with_parse_field(self):
        """Testing UpdateFormMixin.handle_form_request with parse_*_field
        method
        """
        self.mixin.parse_username_field = \
            lambda value, my_state, **kwargs: 'test-%s-%s' % (value, my_state)

        self.spy_on(MyForm.save)

        response = self.mixin.handle_form_request(
            data={
                'username': 'user',
                'password': 'test-pass',
            },
            request=None,
            form_kwargs={
                'custom': True,
            },
            my_state=123)

        user = MyForm.save.last_call.return_value

        self.assertEqual(user.username, 'test-user-123')

        self.assertEqual(
            response,
            (201, {
                'user': user,
            }))

    def test_handle_form_request_with_parse_field_raising_error(self):
        """Testing UpdateFormMixin.handle_form_request with parse_*_field
        methods raising ValidationError
        """
        def _parse_field(value, **kwargs):
            raise ValidationError('This field is just bad.')

        self.mixin.parse_username_field = _parse_field
        self.mixin.parse_password_field = _parse_field

        response = self.mixin.handle_form_request(
            data={
                'username': 'user',
                'password': 'test-pass',
            },
            request=None,
            form_kwargs={
                'custom': True,
            },
            my_state=123)

        self.assertEqual(
            response,
            (INVALID_FORM_DATA, {
                'fields': {
                    'username': ['This field is just bad.'],
                    'password': ['This field is just bad.'],
                },
            }))

    def test_save_form(self):
        """Testing UpdateFormMixin.save_form"""
        form = MyForm(data={
            'username': 'test-user',
            'password': 'test-pass',
        })
        self.assertTrue(form.is_valid())

        user = self.mixin.save_form(form)

        self.assertEqual(user.username, 'test-user')
        self.assertEqual(user.pk, 1)
        self.assertEqual(User.objects.get(pk=1), user)

    def test_save_form_with_save_kwargs(self):
        """Testing UpdateFormMixin.save_form with save_kwargs"""
        form = MyForm(data={
            'username': 'test-user',
            'password': 'test-pass',
        })
        self.assertTrue(form.is_valid())

        user = self.mixin.save_form(form, save_kwargs={'commit': False})

        self.assertEqual(user.username, 'test-user')
        self.assertIsNone(user.pk)
        self.assertFalse(User.objects.exists())

from __future__ import unicode_literals

from django.utils import six

from djblets.testing.testcases import TestCase
from djblets.webapi.resources.base import WebAPIResource
from djblets.webapi.resources.mixins.api_tokens import ResourceAPITokenMixin
from djblets.webapi.resources.root import RootResource
from djblets.webapi.models import BaseWebAPIToken


class PolicyTestResource(ResourceAPITokenMixin, WebAPIResource):
    policy_id = 'test'


class SomeObjectResource(ResourceAPITokenMixin, WebAPIResource):
    policy_id = 'someobject'


root_resource = RootResource([
    SomeObjectResource(),
])


class APIPolicyWebAPIToken(BaseWebAPIToken):
    @classmethod
    def get_root_resource(self):
        return root_resource


class APIPolicyTests(TestCase):
    """Tests API policy through WebAPITokens."""
    def setUp(self):
        super(APIPolicyTests, self).setUp()

        self.resource = PolicyTestResource()

    def test_default_policy(self):
        """Testing API policy enforcement with default policy"""
        self.assert_policy(
            {},
            allowed_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_allow_all(self):
        """Testing API policy enforcement with *.allow=*"""
        self.assert_policy(
            {
                '*': {
                    'allow': ['*'],
                }
            },
            allowed_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_block_all(self):
        """Testing API policy enforcement with *.block=*"""
        self.assert_policy(
            {
                '*': {
                    'block': ['*'],
                }
            },
            blocked_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_block_all_and_resource_allow_all(self):
        """Testing API policy enforcement with *.block=* and
        <resource>.*.allow=*
        """
        self.assert_policy(
            {
                '*': {
                    'block': ['*'],
                },
                'test': {
                    '*': {
                        'allow': ['*'],
                    },
                }
            },
            allowed_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_allow_all_and_resource_block_all(self):
        """Testing API policy enforcement with *.allow=* and
        <resource>.*.block=*
        """
        self.assert_policy(
            {
                '*': {
                    'allow': ['*'],
                },
                'test': {
                    '*': {
                        'block': ['*'],
                    },
                }
            },
            blocked_methods=['HEAD', 'GET', 'POST', 'PATCH', 'PUT', 'DELETE'])

    def test_global_block_all_and_resource_all_allow_methods(self):
        """Testing API policy enforcement with *.block=* and
        <resource>.*.allow=[methods]
        """
        self.assert_policy(
            {
                '*': {
                    'block': ['*'],
                },
                'test': {
                    '*': {
                        'allow': ['GET', 'PUT'],
                    },
                }
            },
            allowed_methods=['GET', 'PUT'],
            blocked_methods=['HEAD', 'POST', 'PATCH', 'DELETE'])

    def test_global_allow_all_and_resource_all_block_specific(self):
        """Testing API policy enforcement with *.allow=* and
        <resource>.*.block=[methods]
        """
        self.assert_policy(
            {
                '*': {
                    'allow': ['*'],
                },
                'test': {
                    '*': {
                        'block': ['GET', 'PUT'],
                    },
                }
            },
            allowed_methods=['HEAD', 'POST', 'PATCH', 'DELETE'],
            blocked_methods=['GET', 'PUT'])

    def test_resource_block_all_and_allow_methods(self):
        """Testing API policy enforcement with <resource>.*.block=* and
        <resource>.*.allow=[methods] for specific methods
        """
        self.assert_policy(
            {
                'test': {
                    '*': {
                        'block': ['*'],
                        'allow': ['GET', 'PUT'],
                    }
                }
            },
            allowed_methods=['GET', 'PUT'],
            blocked_methods=['HEAD', 'POST', 'PATCH', 'DELETE'])

    def test_resource_allow_all_and_block_methods(self):
        """Testing API policy enforcement with <resource>.*.allow=* and
        <resource>.*.block=[methods] for specific methods
        """
        self.assert_policy(
            {
                'test': {
                    '*': {
                        'allow': ['*'],
                        'block': ['GET', 'PUT'],
                    },
                }
            },
            allowed_methods=['HEAD', 'POST', 'DELETE'],
            blocked_methods=['GET', 'PUT'])

    def test_id_allow_all(self):
        """Testing API policy enforcement with <resource>.<id>.allow=*"""
        self.assert_policy(
            {
                'test': {
                    '42': {
                        'allow': ['*'],
                    }
                }
            },
            resource_id=42,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_id_block_all(self):
        """Testing API policy enforcement with <resource>.<id>.block=*"""
        policy = {
            'test': {
                '42': {
                    'block': ['*'],
                }
            }
        }

        self.assert_policy(
            policy,
            resource_id=42,
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

        self.assert_policy(
            policy,
            resource_id=100,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_resource_block_all_and_id_allow_all(self):
        """Testing API policy enforcement with <resource>.*.block=* and
        <resource>.<id>.allow=*
        """
        policy = {
            'test': {
                '*': {
                    'block': ['*'],
                },
                '42': {
                    'allow': ['*'],
                }
            }
        }

        self.assert_policy(
            policy,
            resource_id=42,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

        self.assert_policy(
            policy,
            resource_id=100,
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_resource_allow_all_and_id_block_all(self):
        """Testing API policy enforcement with <resource>.<id>.allow=* and
        <resource>.<id>.block=*
        """
        policy = {
            'test': {
                '*': {
                    'allow': ['*'],
                },
                '42': {
                    'block': ['*'],
                }
            }
        }

        self.assert_policy(
            policy,
            resource_id=42,
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

        self.assert_policy(
            policy,
            resource_id=100,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_global_block_all_and_id_allow_all(self):
        """Testing API policy enforcement with *.<id>.block=* and
        <resource>.<id>.allow=*
        """
        self.assert_policy(
            {
                '*': {
                    'block': ['*'],
                },
                'test': {
                    '42': {
                        'allow': ['*'],
                    }
                }
            },
            resource_id=42,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_global_allow_all_and_id_block_all(self):
        """Testing API policy enforcement with *.<id>.allow=* and
        <resource>.<id>.block=*"""
        policy = {
            '*': {
                'allow': ['*'],
            },
            'test': {
                '42': {
                    'block': ['*'],
                }
            }
        }

        self.assert_policy(
            policy,
            resource_id=42,
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

        self.assert_policy(
            policy,
            resource_id=100,
            allowed_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def test_policy_methods_conflict(self):
        """Testing API policy enforcement with methods conflict"""
        self.assert_policy(
            {
                'test': {
                    '*': {
                        'allow': ['*'],
                        'block': ['*'],
                    },
                }
            },
            blocked_methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])

    def assert_policy(self, policy, allowed_methods=[], blocked_methods=[],
                      resource_id=None):
        if resource_id is not None:
            resource_id = six.text_type(resource_id)

        for method in allowed_methods:
            allowed = self.resource.is_resource_method_allowed(
                policy, method, resource_id)

            if not allowed:
                self.fail('Expected %s to be allowed, but was blocked'
                          % method)

        for method in blocked_methods:
            allowed = self.resource.is_resource_method_allowed(
                policy, method, resource_id)

            if allowed:
                self.fail('Expected %s to be blocked, but was allowed'
                          % method)


class APIPolicyValidationTests(TestCase):
    """Tests API policy validation."""
    def test_empty(self):
        """Testing BaseWebAPIToken.validate_policy with empty policy"""
        APIPolicyWebAPIToken.validate_policy({})

    def test_not_object(self):
        """Testing BaseWebAPIToken.validate_policy without JSON object"""
        self.assertRaisesValidationError(
            'The policy must be a JSON object.',
            APIPolicyWebAPIToken.validate_policy,
            [])

    #
    # Top-level 'resources' object
    #

    def test_no_resources_section(self):
        """Testing BaseWebAPIToken.validate_policy with non-empty policy and
        no resources section
        """
        self.assertRaisesValidationError(
            'The policy is missing a "resources" section.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'foo': {}
            })

    def test_resources_empty(self):
        """Testing BaseWebAPIToken.validate_policy with empty resources section
        """
        self.assertRaisesValidationError(
            'The policy\'s "resources" section must not be empty.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {}
            })

    def test_resources_invalid_format(self):
        """Testing BaseWebAPIToken.validate_policy with resources not an object
        """
        self.assertRaisesValidationError(
            'The policy\'s "resources" section must be a JSON object.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': []
            })

    #
    # '*' section
    #

    def test_global_valid(self):
        """Testing BaseWebAPIToken.validate_policy with valid '*' section"""
        APIPolicyWebAPIToken.validate_policy({
            'resources': {
                '*': {
                    'allow': ['*'],
                    'block': ['POST'],
                }
            }
        })

    def test_empty_global(self):
        """Testing BaseWebAPIToken.validate_policy with empty '*' section"""
        self.assertRaisesValidationError(
            'The "resources.*" section must have "allow" and/or "block" '
            'rules.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    '*': {}
                }
            })

    def test_global_not_object(self):
        """Testing BaseWebAPIToken.validate_policy with '*' section not a
        JSON object
        """
        self.assertRaisesValidationError(
            'The "resources.*" section must be a JSON object.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    '*': []
                }
            })

    def test_global_allow_not_list(self):
        """Testing BaseWebAPIToken.validate_policy with *.allow not a list"""
        self.assertRaisesValidationError(
            'The "resources.*" section\'s "allow" rule must be a list.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    '*': {
                        'allow': {}
                    }
                }
            })

    def test_global_block_not_list(self):
        """Testing BaseWebAPIToken.validate_policy with *.block not a list"""
        self.assertRaisesValidationError(
            'The "resources.*" section\'s "block" rule must be a list.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    '*': {
                        'block': {}
                    }
                }
            })

    #
    # resource-specific '*' section
    #

    def test_resource_global_valid(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.* valid"""
        APIPolicyWebAPIToken.validate_policy({
            'resources': {
                'someobject': {
                    '*': {
                        'allow': ['*'],
                        'block': ['POST'],
                    },
                }
            }
        })

    def test_resource_global_empty(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.* empty"""
        self.assertRaisesValidationError(
            'The "resources.someobject.*" section must have "allow" and/or '
            '"block" rules.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'someobject': {
                        '*': {}
                    }
                }
            })

    def test_resource_global_invalid_policy_id(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.* with
        invalid policy ID
        """
        self.assertRaisesValidationError(
            '"foobar" is not a valid resource policy ID.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'foobar': {
                        '*': {
                            'allow': ['*'],
                        }
                    }
                }
            })

    def test_resource_global_not_object(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.* not an
        object
        """
        self.assertRaisesValidationError(
            'The "resources.someobject.*" section must be a JSON object.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'someobject': {
                        '*': []
                    }
                }
            })

    def test_resource_global_allow_not_list(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.*.allow not
        a list
        """
        self.assertRaisesValidationError(
            'The "resources.someobject.*" section\'s "allow" rule must be a '
            'list.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'someobject': {
                        '*': {
                            'allow': {}
                        }
                    }
                }
            })

    def test_resource_global_block_not_list(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.*.block not
        a list
        """
        self.assertRaisesValidationError(
            'The "resources.someobject.*" section\'s "block" rule must be a '
            'list.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'someobject': {
                        '*': {
                            'block': {}
                        }
                    }
                }
            })

    #
    # resource-specific ID section
    #

    def test_resource_id_valid(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.<id> valid
        """
        APIPolicyWebAPIToken.validate_policy({
            'resources': {
                'someobject': {
                    '42': {
                        'allow': ['*'],
                        'block': ['POST'],
                    },
                }
            }
        })

    def test_resource_id_empty(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.<id> empty
        """
        self.assertRaisesValidationError(
            'The "resources.someobject.42" section must have "allow" and/or '
            '"block" rules.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'someobject': {
                        '42': {}
                    }
                }
            })

    def test_resource_id_invalid_id_type(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.<id> with
        invalid ID type
        """
        self.assertRaisesValidationError(
            '42 must be a string in "resources.someobject"',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'someobject': {
                        42: {
                            'allow': ['*'],
                        }
                    }
                }
            })

    def test_resource_id_not_object(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.<id> not an
        object
        """
        self.assertRaisesValidationError(
            'The "resources.someobject.42" section must be a JSON object.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'someobject': {
                        '42': []
                    }
                }
            })

    def test_resource_id_allow_not_list(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.<id>.allow
        not a list
        """
        self.assertRaisesValidationError(
            'The "resources.someobject.42" section\'s "allow" rule must '
            'be a list.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'someobject': {
                        '42': {
                            'allow': {}
                        }
                    }
                }
            })

    def test_resource_id_block_not_list(self):
        """Testing BaseWebAPIToken.validate_policy with <resource>.<id>.block
        not a list
        """
        self.assertRaisesValidationError(
            'The "resources.someobject.42" section\'s "block" rule must '
            'be a list.',
            APIPolicyWebAPIToken.validate_policy,
            {
                'resources': {
                    'someobject': {
                        '42': {
                            'block': {}
                        }
                    }
                }
            })

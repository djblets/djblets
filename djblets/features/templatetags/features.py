"""Template tags for working with features."""

from __future__ import unicode_literals

from django import template
from django.template.base import (Node, NodeList, TemplateSyntaxError,
                                  token_kwargs)
from django.utils import six

from djblets.features.registry import get_features_registry


register = template.Library()


class IfFeatureNode(Node):
    """Template node for feature-based if statements.

    This works mostly like a standard ``{% if %}`` tag, checking whether the
    given feature is enabled and rendering the content between it and the
    else/end tags only if matching the desired state.

    This supports a ``{% else %}``, to allow rendering content if the feature
    does not match the desired state.

    This is used by both the
    :py:class:`{% if_feature_enabled %} <if_feature_enabled>` and
    :py:class:`{% if_feature_disabled %} <if_feature_disabled>` tags.
    """

    child_nodelists = ('nodelist_true', 'nodelist_false')

    def __init__(self, nodelist_enabled, nodelist_disabled, feature_id,
                 extra_kwargs):
        """Initialize the template node.

        Args:
            nodelist_enabled (django.template.NodeList):
                The nodelist to render if the feature is enabled.

            nodelist_disabled (django.template.NodeList):
                The nodelist to render if the feature is disabled.

            feature_id (unicode):
                The ID of the feature to check.

            extra_kwargs (dict):
                Extra keyword arguments to pass to
                :py:meth:`Feature.is_enabled()
                <djblets.features.feature.Feature.is_enabled>`.
        """

        self.nodelist_enabled = nodelist_enabled
        self.nodelist_disabled = nodelist_disabled
        self.feature_id = feature_id
        self.extra_kwargs = extra_kwargs

    def __repr__(self):
        """Return a representation of the node.

        This is mostly used for debugging output.

        Returns:
            unicode:
            A representation of this node.
        """
        return '<IfFeatureNode for %s>' % self.feature_id

    def render(self, context):
        """Render the node.

        This will determine if the feature is enabled or disabled, and render
        the appropriate list of nodes to a string.

        Args:
            context (django.template.Context):
                The context provided by the template.

        Returns:
            unicode:
            The rendered content as a string.
        """
        feature_id = self.feature_id.resolve(context, True)
        extra_kwargs = {
            key: value.resolve(context)
            for key, value in six.iteritems(self.extra_kwargs)
        }

        feature = get_features_registry().get_feature(feature_id)

        if feature:
            enabled = feature.is_enabled(request=context.get('request'),
                                         **extra_kwargs)
        else:
            enabled = False

        if enabled:
            return self.nodelist_enabled.render(context)
        else:
            return self.nodelist_disabled.render(context)


def _if_feature(parser, token, enabled_first):
    """Common implementation for feature-based if statements.

    This constructs a :py:class:`IfFeatureNode` for the consuming template tag,
    allowing for "if" and "if not" checks.

    Args:
        parser (django.template.Parser):
            The parser being used to parse this template tag.

        token (django.template.Token):
            The token representing this template tag.

        enabled_first (bool):
            If ``True``, this behaves as an "if enabled" check.
            If ``False``, this behaves as a "if disabled' check.

    Returns:
        IfFeatureNode:
        The feature checker node to use for the template.
    """
    bits = token.split_contents()
    tag = bits[0]
    end_tag = 'end%s' % tag

    if len(bits) < 2:
        raise TemplateSyntaxError('%r requires a feature ID argument'
                                  % tag)

    nodelist_1 = parser.parse(('else', end_tag))
    token = parser.next_token()

    if token.contents == 'else':
        nodelist_2 = parser.parse((end_tag,))
        parser.delete_first_token()
    else:
        nodelist_2 = NodeList()

    if enabled_first:
        nodelist_enabled = nodelist_1
        nodelist_disabled = nodelist_2
    else:
        nodelist_disabled = nodelist_1
        nodelist_enabled = nodelist_2

    feature_id = parser.compile_filter(bits[1])
    remaining_bits = bits[2:]
    extra_kwargs = token_kwargs(remaining_bits, parser)

    if remaining_bits:
        raise TemplateSyntaxError('%r received an invalid token: %r'
                                  % (tag, remaining_bits[0]))

    return IfFeatureNode(nodelist_enabled, nodelist_disabled, feature_id,
                         extra_kwargs)


@register.tag
def if_feature_enabled(parser, token):
    """Render content only if a feature is enabled.

    This works mostly like a standard ``{% if %}`` tag, checking if the
    given feature is enabled before rendering the content between it and the
    else or end tags.

    This supports a ``{% else %}``, to allow rendering alternative content if
    the feature is disabled instead.

    It also accepts additional keyword arguments that can be passed to
    :py:meth:`Feature.is_enabled()
    <djblets.features.feature.Feature.is_enabled>`.

    Args:
        parser (django.template.Parser):
            The parser being used to parse this template tag.

        token (django.template.Token):
            The token representing this template tag.

    Returns:
        IfFeatureNode:
        The feature checker node to use for the template.

    Example:
        .. code-block:: html+django

           {% if_feature_enabled "my-feature" user=request.user %}
           This will only render if the feature is enabled for the user.
           {% else %}
           This will only render if the feature is disabled for the user.
           {% endif_feature_enabled %}
    """
    return _if_feature(parser, token, enabled_first=True)


@register.tag
def if_feature_disabled(parser, token):
    """Render content only if a feature is disabled.

    This works mostly like a standard ``{% if %}`` tag, checking if the
    given feature is disabled before rendering the content between it and the
    else or end tags.

    This supports a ``{% else %}``, to allow rendering alternative content if
    the feature is enabled instead.

    It also accepts additional keyword arguments that can be passed to
    :py:meth:`Feature.is_enabled()
    <djblets.features.feature.Feature.is_enabled>`.

    Args:
        parser (django.template.Parser):
            The parser being used to parse this template tag.

        token (django.template.Token):
            The token representing this template tag.

    Returns:
        IfFeatureNode:
        The feature checker node to use for the template.

    Example:
        .. code-block:: html+django

           {% if_feature_disabled "my-feature" user=request.user %}
           This will only render if the feature is disabled for the user.
           {% else %}
           This will only render if the feature is enabled for the user.
           {% endif_feature_disabled %}
    """
    return _if_feature(parser, token, enabled_first=False)

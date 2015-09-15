from hashlib import md5
import django
from django import template
from django.template import Library, Node, VariableDoesNotExist
from picker import models as picker
from ..utils import is_valid_email, get_templates
try:
    import ipdb as pdb
except ImportError:
    import pdb

register = Library()
GRAVATAR_BASE_URL = 'http://www.gravatar.com/avatar/'

#-------------------------------------------------------------------------------
@register.filter
def picker_user_image(user, size=None):
    if not is_valid_email(user.email):
        return ''
        
    return '%s%s.jpg?d=wavatar%s' % (
        GRAVATAR_BASE_URL,
        md5(user.email.strip().lower()).hexdigest(),
        '&s={}'.format(size) if size else ''
    )


#===============================================================================
class MemoizeNode(Node):
    
    #---------------------------------------------------------------------------
    def __init__(self, variable, nodelist):
        self.variable = variable
        self.nodelist = nodelist
        
    #---------------------------------------------------------------------------
    def __repr__(self):
        return "<Memoize node>"

    #---------------------------------------------------------------------------
    def render(self, context):
        memo = self.nodelist.render(context)
        context[self.variable] = memo
        return memo


#-------------------------------------------------------------------------------
@register.tag
def memoize(parser, token):
    bits = token.contents.split()
    if len(bits) != 2:
        raise TemplateSyntaxError("Invalid 'memoize' statement")
        
    nodelist = parser.parse(('endmemoize',))
    parser.delete_first_token()
    return MemoizeNode(bits[1], nodelist)


#-------------------------------------------------------------------------------
@register.simple_tag(takes_context=True, name='pdb')
def pdb_debug(parser, token):
    """Tag that inspects template context.

    Usage: 
    {% pdb %}

    You can then access your context variables directly at the prompt.
    """
    pdb.set_trace()
    return ''


#-------------------------------------------------------------------------------
@register.filter
def verbose(value, arg):
    '''
    From http://www.djangosnippets.org/snippets/795/
    
    Replace this::

        {% if name %} Hello {{ name }}, this is a dummy text {% endif %}

    By this::

        {{ name|verbose:"Hello %s this is a dummy text" }}

    This is also usefull for HTML::

        {{ image|verbose:"<img src=\"%s\" />" }}
    '''
    if not value:
        return ''
        
    try:    
        return arg % value
    except Exception:
        return str(value)


#-------------------------------------------------------------------------------
@register.inclusion_tag('picker/season_nav.html', takes_context=True)
def season_nav(context, week, relative_to):
    return {
        'week': week,
        'relative_to': relative_to,
        'user': context['user'],
        'league': context['league']
    }


#-------------------------------------------------------------------------------
@register.inclusion_tag('picker/all_seasons_nav.html', takes_context=True)
def all_seasons_nav(context, current, league, relative_to):
    return {
        'label': 'All seasons',
        'current' :int(current),
        'relative_to': relative_to,
        'user': context['user'],
        'league': context['league']
    }


#-------------------------------------------------------------------------------
@register.filter
def is_management(user):
    return user.is_superuser



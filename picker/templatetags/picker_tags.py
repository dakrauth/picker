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


#===============================================================================
class HavingNode(template.Node):
    
    #---------------------------------------------------------------------------
    def __init__(self, having_var, context_var, nodelist, nodelist_else):
        self.having_var = having_var
        self.context_var = context_var
        self.nodelist = nodelist
        self.nodelist_else = nodelist_else
    
    #---------------------------------------------------------------------------
    def render(self, context):
        value = self.having_var.resolve(context)
        if value:
            with context.push(**{self.context_var: value}):
                return self.nodelist.render(context)

        if self.nodelist_else:
            return self.nodelist_else.render(context)
            
        return ''


#-------------------------------------------------------------------------------
@register.tag('having')
def do_having(parser, token):
    having_err_msg = "'having' statements should use the format 'having x as y': '{}'"
    bits = token.split_contents()
    if len(bits) < 4:
        raise template.TemplateSyntaxError(having_err_msg.format(token.contents))

    tag_name, having_var, _as, context_var = bits
    having_var = parser.compile_filter(having_var)
    if _as != 'as':
        raise template.TemplateSyntaxError(having_err_msg.format(token.contents))

    nodelist = parser.parse(('else', 'endhaving',))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_else = parser.parse(('endhaving',))
        parser.delete_first_token()
    else:
        nodelist_else = None
        
    return HavingNode(having_var, context_var, nodelist, nodelist_else)


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
@register.simple_tag(name='pdb')
def pdb_debug(*args, **kws):
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
    league = context['league']
    return {
        'week': week,
        'relative_to': relative_to,
        'user': context['user'],
        'league': league,
        'season_weeks': league.season_weeks(context.get('season', None))
    }


#-------------------------------------------------------------------------------
@register.inclusion_tag('picker/season_nav_all.html', takes_context=True)
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



from django import forms
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.template import loader, TemplateDoesNotExist


class TemplateTeamChoice(forms.RadioSelect):
    picker_template_name = "picker/team_pick_field.html"

    def __init__(self, *args, **kws):
        super(TemplateTeamChoice, self).__init__(*args, **kws)

    def render(self, name, value, attrs=None, renderer=None):
        try:
            tmpl = loader.get_template(self.picker_template_name)
        except TemplateDoesNotExist:
            return super(TemplateTeamChoice, self).render(name, value, attrs)

        labels = ""
        str_value = force_str(value if value is not None else "")
        final_attrs = self.build_attrs(attrs)
        for i, (game_id, team) in enumerate(self.choices):
            readonly = bool("readonly" in final_attrs)
            labels += tmpl.render(
                {
                    "home_away": "home" if i else "away",
                    "choice_id": "%s_%s" % (attrs["id"], game_id),
                    "name": name,
                    "team": team,
                    "checked": "checked" if game_id == str_value else "",
                    "value": game_id,
                    "readonly": "readonly" if readonly else "",
                    "disabled": "disabled" if readonly else "",
                }
            )

        return mark_safe(labels)

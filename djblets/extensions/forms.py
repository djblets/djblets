from django import forms


class SettingsForm(forms.Form):
    """
    A base form for loading/saving settings for an extension. This is meant
    to be overridden by extensions to provide configuration pages. Any fields
    defined by the form will be loaded and saved automatically.
    """
    def __init__(self, extension, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.extension = extension

        for field in self.fields:
            if field in self.extension.settings:
                self.fields[field].initial = self.extension.settings[field]

    def save(self):
        if not self.errors:
            for key, value in self.cleaned_data.iteritems():
                self.extension.settings[key] = value

            self.extension.settings.save()

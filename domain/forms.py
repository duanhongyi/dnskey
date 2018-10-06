from django import forms

from .models import Domain, Record


class DomainForm(forms.ModelForm):

    def clean_name(self):
        name = self.cleaned_data['name']
        if not name.endswith('.'):
            raise forms.ValidationError('name must be ends with .')
        return name

    class Meta:
        model = Domain
        fields = '__all__'


class RecordForm(forms.ModelForm):

    def clean_subdomain(self):
        domain = self.cleaned_data['domain']
        subdomain = self.cleaned_data['subdomain']
        if int(self.data['rtype']) == 5:  # CNAME
            if Record.objects.filter(
                subdomain=subdomain, domain=domain).exclude(
                    rtype=5).exists():
                raise forms.ValidationError('111 add record error, see RFC 1034 .')
        else:
            if Record.objects.filter(
                subdomain=subdomain, domain=domain, rtype=5).exists():
                raise forms.ValidationError('add record error, see RFC 1034 .')
        return subdomain

    class Meta:
        model = Record
        fields = '__all__'

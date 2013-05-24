from django.utils.translation import gettext_lazy as _
import json
from django import forms
from django.core.validators import ValidationError
from bdphpcprovider.simpleui import validators

class SweepSubmitForm(forms.Form):

    number_vm_instances = forms.IntegerField()
    input_location = forms.CharField(label=_("Input Location"),
        max_length=255,
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 1}))
    number_of_dimensions = forms.IntegerField(min_value=0,
        label=_("Degrees of Variation"), help_text="degrees of freedom")
    threshold = forms.CharField(label=_("Threshold"),
            max_length=255
        )
    iseed = forms.IntegerField(min_value=0)
    error_threshold = forms.DecimalField()

    max_iteration = forms.IntegerField(min_value=1)
    pottype = forms.IntegerField(min_value=0)
    experiment_id = forms.IntegerField(required=False)
    sweep_map = forms.CharField(label="Sweep Map JSON",
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 10}
        ))
    run_map = forms.CharField(label="Run Map JSON",
        widget=forms.Textarea(attrs={'cols': 80, 'rows': 10}
        ))

    def __init__(self, *args, **kwargs):
        super(SweepSubmitForm, self).__init__(*args, **kwargs)
        self.fields["sweep_map"].validators.append(validators.validate_sweep_map)
        self.fields["run_map"].validators.append(validators.validate_run_map)
        self.fields["number_vm_instances"].validators.append(validators.validate_number_vm_instances)
        self.fields["number_of_dimensions"].validators.append(validators.validate_number_of_dimensions)
        self.fields["threshold"].validators.append(validators.validate_threshold)
        self.fields["iseed"].validators.append(validators.validate_iseed)
        self.fields["pottype"].validators.append(validators.validate_pottype)
        self.fields["max_iteration"].validators.append(validators.validate_max_iteration)
        self.fields["error_threshold"].validators.append(validators.validate_error_threshold)
        self.fields["experiment_id"].validators.append(validators.validate_experiment_id)
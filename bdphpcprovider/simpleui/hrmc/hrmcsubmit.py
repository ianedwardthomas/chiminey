from django.utils.translation import gettext_lazy as _
from django import forms
from bdphpcprovider.simpleui import validators


class HRMCSubmitForm(forms.Form):

    number_vm_instances = forms.IntegerField(min_value=0,help_text="Ensure tenancy has sufficient resources")
    input_location = forms.CharField(label=_("Input Location"),
        max_length=255,
        widget=forms.TextInput,
        help_text="A BDPUrl Directory"
    )
    number_of_dimensions = forms.IntegerField(min_value=0, label=_("Degrees of Variation"))
    threshold = forms.CharField(label=_("Threshold"),
            max_length=255,
            widget=forms.TextInput,
        )
    iseed = forms.IntegerField(min_value=0,help_text="help")
    error_threshold = forms.DecimalField()

    max_iteration = forms.IntegerField(min_value=1)
    pottype = forms.IntegerField(min_value=0)

    experiment_id = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        super(HRMCSubmitForm, self).__init__(*args, **kwargs)
        self.fields["number_vm_instances"].validators.append(validators.validate_number_vm_instances)
        self.fields["number_of_dimensions"].validators.append(validators.validate_number_of_dimensions)
        self.fields["threshold"].validators.append(validators.validate_threshold)
        self.fields["iseed"].validators.append(validators.validate_iseed)
        self.fields["pottype"].validators.append(validators.validate_pottype)
        self.fields["max_iteration"].validators.append(validators.validate_max_iteration)
        self.fields["error_threshold"].validators.append(validators.validate_error_threshold)
        self.fields["experiment_id"].validators.append(validators.validate_experiment_id)




    # ['http://rmit.edu.au/schemas/hrmc',
    #     ('number_vm_instances', 2), (u'iseed', 42),
    #     # TODO: in configure stage could copy this information from somewhere to this required location
    #     ('input_location',  'file://127.0.0.1/hrmcrun/input_0'),
    #     ('number_dimensions', 1),
    #     ('threshold', "[1]"),
    #     ('error_threshold', "0.03"),
    #     ('max_iteration', 20)



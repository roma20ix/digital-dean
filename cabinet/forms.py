from django import forms


class RequestForm(forms.Form):
    kind = forms.ChoiceField(label="Тип заявки", choices=[
        ("certificate", "Справка об обучении"), ("appeal", "Обращение в деканат"),
    ])
    message = forms.CharField(label="Текст обращения", widget=forms.Textarea, required=False)
    submission_token = forms.UUIDField(widget=forms.HiddenInput)

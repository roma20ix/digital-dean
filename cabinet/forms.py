from uuid import UUID, uuid4

from django import forms
from django.core.signing import BadSignature, Signer

from .models import StudentRequest


class RequestForm(forms.Form):
    kind = forms.ChoiceField(label="Тип заявки", choices=StudentRequest.Kind.choices)
    message = forms.CharField(label="Текст обращения", widget=forms.Textarea, required=False)
    submission_token = forms.CharField(widget=forms.HiddenInput, error_messages={
        "required": "Обновите страницу, чтобы получить новую форму.",
    })

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.signer = Signer(salt=f"cabinet.request.{user.pk}")
        if not self.is_bound:
            self.initial["submission_token"] = self.signer.sign(str(uuid4()))

    def clean_submission_token(self):
        try:
            return UUID(self.signer.unsign(self.cleaned_data["submission_token"]))
        except (BadSignature, ValueError):
            raise forms.ValidationError("Форма недействительна. Откройте новую форму.")

    def clean(self):
        data = super().clean()
        if data.get("kind") == StudentRequest.Kind.APPEAL and not data.get("message"):
            self.add_error("message", "Введите текст обращения в деканат.")
        return data

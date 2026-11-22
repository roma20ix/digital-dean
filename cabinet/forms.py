from io import BytesIO
from uuid import UUID, uuid4

from django import forms
from django.core.signing import BadSignature, Signer

from PIL import Image, ImageOps

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


class AppearanceForm(forms.Form):
    photo = forms.FileField(label="Новое изображение", required=False,
                            widget=forms.FileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}))
    remove = forms.BooleanField(label="Вернуть инициалы", required=False)

    def clean_photo(self):
        photo = self.cleaned_data["photo"]
        if not photo:
            return None
        if photo.size > 4 * 1024 * 1024:
            raise forms.ValidationError("Выберите изображение до 4 МБ.")
        try:
            with Image.open(photo, formats=("JPEG", "PNG", "WEBP")) as image:
                if image.width * image.height > 16_000_000:
                    raise forms.ValidationError("Выберите изображение до 16 мегапикселей.")
                image = ImageOps.exif_transpose(image).convert("RGB")
                thumbnail = ImageOps.fit(image, (256, 256), method=Image.Resampling.LANCZOS)
                output = BytesIO()
                thumbnail.save(output, format="JPEG", quality=85)
                return output.getvalue()
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
            raise forms.ValidationError("Выберите исправное изображение JPG, PNG или WebP.")

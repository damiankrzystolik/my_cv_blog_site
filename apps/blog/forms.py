from django import forms

from .models import Comment


class CommentForm(forms.ModelForm):
    # Pułapka na boty: pole ukryte CSS-em, człowiek go nie wypełni.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}))

    class Meta:
        model = Comment
        fields = ["name", "email", "body"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def is_spam(self):
        return bool(self.cleaned_data.get("website"))


class SearchForm(forms.Form):
    query = forms.CharField(
        label="",
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Wpisz szukaną frazę…"}),
    )

    def clean_query(self):
        query = self.cleaned_data["query"].strip()
        if len(query) < 2:
            raise forms.ValidationError("Fraza musi mieć co najmniej 2 znaki.")
        return query

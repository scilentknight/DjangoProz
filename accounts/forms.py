import re
from django import forms
from .models import Account


class RegistrationForm(forms.ModelForm):
    # Override email field to prevent Django's default unique check
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"placeholder": "Enter your email"}),
        label="Email Address",
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Enter password"}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Enter confirm password"}),
    )

    class Meta:
        model = Account
        fields = ["first_name", "last_name", "email", "phone_number", "password"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs["placeholder"] = "Enter firstname"
        self.fields["last_name"].widget.attrs["placeholder"] = "Enter lastname"
        self.fields["email"].widget.attrs["placeholder"] = "Enter your email"
        self.fields["phone_number"].widget.attrs["placeholder"] = "Enter phone number"
        for field in self.fields:
            self.fields[field].widget.attrs["class"] = "form-control"

    def clean_email(self):
        email = self.cleaned_data.get("email")

        # Check if any active user exists with this email
        if Account.objects.filter(email=email, is_active=True).exists():
            raise forms.ValidationError(" with this email already exists.")

        # If inactive user exists, allow registration (view will reuse it)
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        phone_number = cleaned_data.get("phone_number")

        # ---- Phone number validation ----
        if phone_number:
            # Check length first
            if len(phone_number) != 10:
                self.add_error(
                    "phone_number", "Phone number must be exactly 10 digits."
                )

            # Check starting digits separately
            if not phone_number.startswith(("96", "97", "98")):
                self.add_error(
                    "phone_number", "Phone number must start with 96, 97, or 98."
                )

        # ---- Password validations ----
        if password and confirm_password:
            if password != confirm_password:
                self.add_error("password", "Passwords do not match!")

            if len(password) < 8:
                self.add_error(
                    "password", "Password must be at least 8 characters long."
                )

            if not re.search(r"[A-Z]", password):
                self.add_error(
                    "password", "Password must contain at least one uppercase letter."
                )

            if not re.search(r"\d", password):
                self.add_error("password", "Password must contain at least one number.")

            if not re.search(r"[^\w\s]", password):
                self.add_error(
                    "password", "Password must contain at least one special character."
                )

        return cleaned_data

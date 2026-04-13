from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator

from .models import Screenshot


NON_NEGATIVE_VALIDATOR = MinValueValidator(
    0,
    message="Value must be zero or positive.",
)

POSITIVE_VALIDATOR = MinValueValidator(
    0.0000001,
    message="Value must be greater than zero.",
)


def number_widget(placeholder: str, step: str = "any", min_value: str | None = None) -> forms.NumberInput:
    attrs = {
        "class": "form-control rw-form-control",
        "placeholder": placeholder,
        "step": step,
        "autocomplete": "off",
        "inputmode": "decimal",
    }
    if min_value is not None:
        attrs["min"] = min_value
    return forms.NumberInput(attrs=attrs)


def integer_widget(placeholder: str, min_value: str = "1") -> forms.NumberInput:
    return forms.NumberInput(
        attrs={
            "class": "form-control rw-form-control",
            "placeholder": placeholder,
            "step": "1",
            "min": min_value,
            "autocomplete": "off",
            "inputmode": "numeric",
        }
    )


def image_widget() -> forms.ClearableFileInput:
    return forms.ClearableFileInput(
        attrs={
            "class": "form-control rw-form-control",
            "accept": "image/*",
        }
    )


class LotSizeForm(forms.Form):
    lot_size = forms.FloatField(
        label="Lot Size",
        validators=[POSITIVE_VALIDATOR],
        help_text="The number of lots for your planned trade.",
        widget=number_widget("e.g. 1.0", min_value="0.0000001"),
    )
    pip_distance = forms.FloatField(
        label="Pip Distance",
        validators=[POSITIVE_VALIDATOR],
        help_text="Distance in pips between entry and stop loss.",
        widget=number_widget("e.g. 50", min_value="0.0000001"),
    )
    pip_value = forms.FloatField(
        label="Pip Value per Lot",
        validators=[POSITIVE_VALIDATOR],
        help_text="Monetary value of 1 pip per lot.",
        widget=number_widget("e.g. 10", min_value="0.0000001"),
    )


class RiskPerTradeForm(forms.Form):
    account_balance = forms.FloatField(
        label="Account Balance ($)",
        validators=[POSITIVE_VALIDATOR],
        help_text="Total trading capital available for planning.",
        widget=number_widget("e.g. 10000", min_value="0.0000001"),
    )
    lot_size = forms.FloatField(
        label="Lot Size",
        validators=[POSITIVE_VALIDATOR],
        help_text="Number of lots planned for the trade.",
        widget=number_widget("e.g. 1.0", min_value="0.0000001"),
    )
    pip_value = forms.FloatField(
        label="Pip Value per Lot",
        validators=[POSITIVE_VALIDATOR],
        help_text="Monetary value of 1 pip.",
        widget=number_widget("e.g. 10", min_value="0.0000001"),
    )
    stop_loss_pips = forms.FloatField(
        label="Stop Loss (pips)",
        validators=[POSITIVE_VALIDATOR],
        help_text="Distance to stop loss in pips.",
        widget=number_widget("e.g. 20", min_value="0.0000001"),
    )


class StrategyRiskForm(forms.Form):
    base_lot = forms.FloatField(
        label="Base Lot Size",
        validators=[POSITIVE_VALIDATOR],
        help_text="Initial lot size before strategy adjustment.",
        widget=number_widget("e.g. 1.0", min_value="0.0000001"),
    )
    win_rate = forms.FloatField(
        label="Win Rate (%)",
        validators=[
            MinValueValidator(1, message="Win rate must be at least 1%."),
            MaxValueValidator(100, message="Win rate cannot exceed 100%."),
        ],
        help_text="Expected win rate percentage.",
        widget=number_widget("e.g. 60", min_value="1"),
    )
    rr = forms.FloatField(
        label="Risk-Reward Ratio",
        validators=[MinValueValidator(0.1, message="R:R must be at least 0.1.")],
        help_text="Target risk-reward ratio.",
        widget=number_widget("e.g. 2.0", min_value="0.1"),
    )
    volatility = forms.FloatField(
        label="Volatility Factor",
        validators=[MinValueValidator(0.1, message="Volatility factor must be at least 0.1.")],
        help_text="Adjustment factor for volatility.",
        widget=number_widget("e.g. 1.2", min_value="0.1"),
    )


class SLTPForm(forms.Form):
    entry = forms.FloatField(
        label="Entry Price",
        validators=[POSITIVE_VALIDATOR],
        help_text="Planned entry price.",
        widget=number_widget("e.g. 1.2000", min_value="0.0000001"),
    )
    stop_loss = forms.FloatField(
        label="Stop Loss Price",
        validators=[POSITIVE_VALIDATOR],
        help_text="Price at which you exit with a loss.",
        widget=number_widget("e.g. 1.1900", min_value="0.0000001"),
    )
    take_profit = forms.FloatField(
        label="Take Profit Price",
        validators=[POSITIVE_VALIDATOR],
        help_text="Price at which you exit with a profit.",
        widget=number_widget("e.g. 1.2200", min_value="0.0000001"),
    )
    lot_size = forms.FloatField(
        label="Lot Size",
        validators=[POSITIVE_VALIDATOR],
        help_text="Number of lots for the planned trade.",
        widget=number_widget("e.g. 1.0", min_value="0.0000001"),
    )
    pip_value = forms.FloatField(
        label="Pip Value per Lot",
        validators=[POSITIVE_VALIDATOR],
        help_text="Value of one pip in your account currency.",
        widget=number_widget("e.g. 10", min_value="0.0000001"),
    )

    def clean(self):
        cleaned_data = super().clean()

        entry = cleaned_data.get("entry")
        stop_loss = cleaned_data.get("stop_loss")
        take_profit = cleaned_data.get("take_profit")

        if entry is not None and stop_loss is not None and entry == stop_loss:
            self.add_error("stop_loss", "Stop loss must be different from entry price.")

        if entry is not None and take_profit is not None and entry == take_profit:
            self.add_error("take_profit", "Take profit must be different from entry price.")

        if stop_loss is not None and take_profit is not None and stop_loss == take_profit:
            self.add_error("take_profit", "Take profit must be different from stop loss.")

        return cleaned_data


class MonteCarloForm(forms.Form):
    num_simulations = forms.IntegerField(
        label="Number of Simulations",
        min_value=1,
        help_text="How many simulations to run.",
        widget=integer_widget("e.g. 100"),
    )
    num_trades = forms.IntegerField(
        label="Number of Trades",
        min_value=1,
        help_text="Number of trades per simulation.",
        widget=integer_widget("e.g. 1000"),
    )


class ScreenshotForm(forms.ModelForm):
    class Meta:
        model = Screenshot
        fields = ["image"]
        widgets = {
            "image": image_widget(),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if not image:
            return image

        allowed_extensions = (".png", ".jpg", ".jpeg", ".webp", ".gif")
        if not image.name.lower().endswith(allowed_extensions):
            raise ValidationError("Only PNG, JPG, JPEG, WEBP, or GIF files are allowed.")

        max_size_mb = 5
        if image.size > max_size_mb * 1024 * 1024:
            raise ValidationError(f"Image must be {max_size_mb} MB or smaller.")

        return image
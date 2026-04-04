from django import forms
from django.core.validators import MinValueValidator
from .models import Screenshot

float_validator = MinValueValidator(0, message="Value must be zero or positive.")


def number_widget(placeholder: str, step: str = "any") -> forms.NumberInput:
    return forms.NumberInput(
        attrs={
            "class": "form-control rw-form-control",
            "placeholder": placeholder,
            "step": step,
            "autocomplete": "off",
        }
    )


def file_widget() -> forms.ClearableFileInput:
    return forms.ClearableFileInput(
        attrs={
            "class": "form-control rw-form-control",
            "accept": ".csv,.xlsx,.xls,image/*",
        }
    )


class LotSizeForm(forms.Form):
    lot_size = forms.FloatField(
        label="Lot Size",
        validators=[float_validator],
        help_text="The number of lots for your planned trade.",
        widget=number_widget("e.g. 1.0"),
    )
    pip_distance = forms.FloatField(
        label="Pip Distance",
        validators=[float_validator],
        help_text="Distance in pips between entry and stop loss.",
        widget=number_widget("e.g. 50"),
    )
    pip_value = forms.FloatField(
        label="Pip Value per Lot",
        validators=[float_validator],
        help_text="Monetary value of 1 pip per lot.",
        widget=number_widget("e.g. 10"),
    )


class RiskPerTradeForm(forms.Form):
    account_balance = forms.FloatField(
        label="Account Balance ($)",
        validators=[float_validator],
        help_text="Total trading capital available for planning.",
        widget=number_widget("e.g. 10000"),
    )
    lot_size = forms.FloatField(
        label="Lot Size",
        validators=[float_validator],
        help_text="Number of lots planned for the trade.",
        widget=number_widget("e.g. 1.0"),
    )
    pip_value = forms.FloatField(
        label="Pip Value per Lot",
        validators=[float_validator],
        help_text="Monetary value of 1 pip.",
        widget=number_widget("e.g. 10"),
    )
    stop_loss_pips = forms.FloatField(
        label="Stop Loss (pips)",
        validators=[float_validator],
        help_text="Distance to stop loss in pips.",
        widget=number_widget("e.g. 20"),
    )


class StrategyRiskForm(forms.Form):
    base_lot = forms.FloatField(
        label="Base Lot Size",
        validators=[float_validator],
        help_text="Initial lot size before strategy adjustment.",
        widget=number_widget("e.g. 1.0"),
    )
    win_rate = forms.FloatField(
        label="Win Rate (%)",
        validators=[MinValueValidator(1, message="Win rate must be at least 1%.")],
        help_text="Expected win rate percentage.",
        widget=number_widget("e.g. 60"),
    )
    rr = forms.FloatField(
        label="Risk-Reward Ratio",
        validators=[MinValueValidator(0.1, message="R:R must be at least 0.1.")],
        help_text="Target risk-reward ratio.",
        widget=number_widget("e.g. 2.0"),
    )
    volatility = forms.FloatField(
        label="Volatility Factor",
        validators=[MinValueValidator(0.1, message="Volatility factor must be at least 0.1.")],
        help_text="Adjustment factor for volatility.",
        widget=number_widget("e.g. 1.2"),
    )


class SLTPForm(forms.Form):
    entry = forms.FloatField(
        label="Entry Price",
        validators=[float_validator],
        help_text="Planned entry price.",
        widget=number_widget("e.g. 1.2000"),
    )
    stop_loss = forms.FloatField(
        label="Stop Loss Price",
        validators=[float_validator],
        help_text="Price at which you exit with a loss.",
        widget=number_widget("e.g. 1.1900"),
    )
    take_profit = forms.FloatField(
        label="Take Profit Price",
        validators=[float_validator],
        help_text="Price at which you exit with a profit.",
        widget=number_widget("e.g. 1.2200"),
    )
    lot_size = forms.FloatField(
        label="Lot Size",
        validators=[float_validator],
        help_text="Number of lots for the planned trade.",
        widget=number_widget("e.g. 1.0"),
    )
    pip_value = forms.FloatField(
        label="Pip Value per Lot",
        validators=[float_validator],
        help_text="Value of one pip in your account currency.",
        widget=number_widget("e.g. 10"),
    )


class MonteCarloForm(forms.Form):
    num_simulations = forms.IntegerField(
        label="Number of Simulations",
        min_value=1,
        help_text="How many simulations to run.",
        widget=number_widget("e.g. 100", step="1"),
    )
    num_trades = forms.IntegerField(
        label="Number of Trades",
        min_value=1,
        help_text="Number of trades per simulation.",
        widget=number_widget("e.g. 1000", step="1"),
    )


class ScreenshotForm(forms.ModelForm):
    class Meta:
        model = Screenshot
        fields = ["image"]
        widgets = {
            "image": file_widget(),
        }
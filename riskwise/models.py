from django.contrib.auth.models import User
from django.db import models


class TradingAccount(models.Model):
    """
    Supports multiple accounts (Funded, Personal).
    """
    ACCOUNT_CHOICES = [
        ('Funded', 'Funded'),
        ('Personal', 'Personal'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=10, choices=ACCOUNT_CHOICES)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    risk_percent = models.DecimalField(max_digits=5, decimal_places=2, default=2.0, help_text="Default % risk per trade")

    def __str__(self):
        return f"{self.name} ({self.account_type})"


class Trade(models.Model):
    """
    Individual trade records used as reference inputs for risk planning.
    """
    ACCOUNT_CHOICES = [
        ('Funded', 'Funded'),
        ('Personal', 'Personal'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(null=True, blank=True)
    symbol = models.CharField(max_length=20)
    volume = models.FloatField()
    entry_price = models.FloatField()
    exit_price = models.FloatField()
    profit = models.FloatField()
    account_type = models.CharField(max_length=10, choices=ACCOUNT_CHOICES)
    strategy = models.ForeignKey('Strategy', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.symbol} ({self.date})"


class Strategy(models.Model):
    """
    Defines strategy parameters.
    """
    name = models.CharField(max_length=50)
    base_lot_size = models.FloatField()
    target_win_rate = models.FloatField(help_text="Expected win rate (%)")
    target_rr = models.FloatField(help_text="Target Risk/Reward Ratio")
    reference_volatility = models.FloatField(help_text="Reference volatility measure")

    def __str__(self):
        return self.name


class DailyTradeLog(models.Model):
    """
    Tracks daily profit/loss for cumulative risk.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    date = models.DateField(auto_now_add=True)
    trade_name = models.CharField(max_length=200)
    risk_amount = models.DecimalField(max_digits=12, decimal_places=2)
    profit_loss = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.date} - {self.trade_name}"


class Screenshot(models.Model):
    """
    Stores uploaded screenshots for internal project documentation.
    """
    image = models.ImageField(upload_to="screenshots/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Screenshot {self.id}"


class SimulationHistory(models.Model):
    """
    Persists simulation runs for audit, review, and comparison.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    label = models.CharField(max_length=100)
    tags = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    parameters = models.JSONField()
    results = models.JSONField()
    chart_base64 = models.TextField()

    class Meta:
        verbose_name_plural = "Simulation histories"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.label} ({self.created_at:%Y-%m-%d %H:%M})"

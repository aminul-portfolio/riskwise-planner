from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from riskwise.models import SimulationHistory, Strategy, Trade, TradingAccount


class Command(BaseCommand):
    help = "Seed a reviewable RiskWise demo user with baseline trade data and one saved planning run."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo_reviewer")
        parser.add_argument("--password", default="DemoPass123!")
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        password = options["password"]
        reset = options["reset"]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": True, "is_superuser": False},
        )
        if created or not user.check_password(password):
            user.set_password(password)
            user.is_staff = True
            user.save()

        if reset:
            SimulationHistory.objects.filter(user=user).delete()
            Trade.objects.filter(user=user).delete()
            TradingAccount.objects.filter(user=user).delete()

        strategy, _ = Strategy.objects.get_or_create(
            name="Seeded Demo Strategy",
            defaults={
                "base_lot_size": 1.0,
                "target_win_rate": 54.0,
                "target_rr": 1.7,
                "reference_volatility": 1.15,
            },
        )

        TradingAccount.objects.get_or_create(
            user=user,
            name="Demo Capital Preservation Account",
            defaults={
                "account_type": "Personal",
                "balance": 10000.00,
                "risk_percent": 1.50,
            },
        )

        if not Trade.objects.filter(user=user).exists():
            profits = [
                85.0, -42.5, 120.0, -38.0, 66.0, -54.0,
                95.0, -20.0, 140.0, -72.0, 58.0, 44.0,
                -63.0, 110.0, -48.0, 92.0, -35.0, 130.0,
                -27.0, 76.0, 102.0, -41.0, 88.0, -22.0,
            ]
            symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
            base_date = date(2024, 1, 1)

            trade_rows = []
            for idx, profit in enumerate(profits):
                entry_price = 1.1000 + (idx * 0.0015)
                exit_price = entry_price + (profit / 10000.0)
                trade_rows.append(
                    Trade(
                        user=user,
                        date=base_date + timedelta(days=idx),
                        symbol=symbols[idx % len(symbols)],
                        volume=1.0,
                        entry_price=round(entry_price, 5),
                        exit_price=round(exit_price, 5),
                        profit=float(profit),
                        account_type="Personal",
                        strategy=strategy,
                    )
                )

            Trade.objects.bulk_create(trade_rows, batch_size=100)

        if not SimulationHistory.objects.filter(user=user, label="Seeded Stress-Test Run").exists():
            SimulationHistory.objects.create(
                user=user,
                label="Seeded Stress-Test Run",
                tags="demo,seeded",
                parameters={
                    "num_simulations": 1000,
                    "num_trades": 24,
                    "range_start": 0,
                    "range_end": 24,
                    "run_type": "stress_test",
                    "dataset_meta": {
                        "filename": "database_trades_seeded",
                        "source_file": "database_trades_seeded",
                        "trade_count": 24,
                        "records_loaded": 24,
                        "date_start": "2024-01-01",
                        "date_end": "2024-01-24",
                        "has_profit": True,
                        "columns": [
                            "date",
                            "symbol",
                            "volume",
                            "entry_price",
                            "exit_price",
                            "profit",
                            "account_type",
                        ],
                    },
                },
                results={
                    "min": -480.0,
                    "max": 1120.0,
                    "mean": 235.0,
                    "median": 210.0,
                    "p05": -290.0,
                    "p95": 740.0,
                    "prob_positive": 63.5,
                    "p10_final": -180.0,
                    "p25_final": -40.0,
                    "p50_final": 210.0,
                    "p75_final": 420.0,
                    "p90_final": 740.0,
                    "positive_count": 635,
                    "path_count": 1000,
                    "positive_rate": 63.5,
                },
                chart_base64="",
            )

        self.stdout.write(self.style.SUCCESS("Seed demo completed."))
        self.stdout.write(f"Username: {username}")
        self.stdout.write(f"Password: {password}")
        self.stdout.write("Next: log in, open /dashboard/, then open /simulations/history/.")

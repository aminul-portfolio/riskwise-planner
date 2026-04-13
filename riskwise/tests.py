from io import StringIO

import numpy as np
import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from .models import SimulationHistory
from .services import (
    SESSION_DF_KEY,
    SESSION_META_KEY,
    build_dashboard_interpretation,
    build_simulation_warning,
    build_trade_risk_warning,
    calculate_lot_size,
    calculate_sltp,
    calculate_strategy_risk,
    calculate_trade_risk,
    clear_uploaded_dataset_from_session,
    get_active_planning_df,
    load_dataset_meta_from_session,
    load_uploaded_df_from_session,
    prepare_simulation_dataframe,
    prepare_trade_import_dataframe,
    run_simulation,
    save_dataset_meta_to_session,
    save_uploaded_df_to_session,
)

User = get_user_model()


def build_csv_file(
    name="sample_trades.csv",
    content=(
        "date,symbol,volume,entryprice,exitprice,profit,accounttype\n"
        "2024-01-01,EURUSD,1,1.1000,1.1050,50,personal\n"
        "2024-01-02,EURUSD,1,1.1050,1.1000,-30,personal\n"
        "2024-01-03,GBPUSD,1,1.2500,1.2580,80,personal\n"
        "2024-01-04,GBPUSD,1,1.2580,1.2520,-40,personal\n"
        "2024-01-05,USDJPY,1,145.00,145.50,60,personal\n"
        "2024-01-06,USDJPY,1,145.50,145.10,-20,personal\n"
    ),
):
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/csv")


def attach_session(request):
    middleware = SessionMiddleware(lambda req: None)
    middleware.process_request(request)
    request.session.save()
    return request


class AuthenticatedUserMixin:
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def upload_sample_dataset(self, name="sample_trades.csv"):
        file_obj = build_csv_file(name=name)
        return self.client.post(reverse("upload"), {"file": file_obj}, follow=True)


class PublicPageTests(TestCase):
    """Pages accessible without authentication."""

    def test_homepage_returns_200(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_homepage_contains_product_name(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "RiskWise Planner")

    def test_login_page_returns_200(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)


class AuthenticationTests(TestCase):
    """Login-required pages redirect unauthenticated users."""

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_upload_requires_login(self):
        response = self.client.get(reverse("upload"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_lot_size_requires_login(self):
        response = self.client.get(reverse("lot_size"))
        self.assertEqual(response.status_code, 302)

    def test_risk_per_trade_requires_login(self):
        response = self.client.get(reverse("risk_per_trade"))
        self.assertEqual(response.status_code, 302)

    def test_strategy_risk_requires_login(self):
        response = self.client.get(reverse("strategy_risk"))
        self.assertEqual(response.status_code, 302)

    def test_sltp_requires_login(self):
        response = self.client.get(reverse("sltp"))
        self.assertEqual(response.status_code, 302)

    def test_monte_carlo_requires_login(self):
        response = self.client.get(reverse("monte_carlo"))
        self.assertEqual(response.status_code, 302)

    def test_simulation_run_requires_login(self):
        response = self.client.get(reverse("simulation_run"))
        self.assertEqual(response.status_code, 302)

    def test_simulation_scenario_requires_login(self):
        response = self.client.get(reverse("simulation_scenario"))
        self.assertEqual(response.status_code, 302)

    def test_simulation_history_requires_login(self):
        response = self.client.get(reverse("simulation_history"))
        self.assertEqual(response.status_code, 302)


class AuthenticatedPageTests(AuthenticatedUserMixin, TestCase):
    """Pages that require login return correctly for authenticated users."""

    def test_dashboard_no_data(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No active planning baseline")

    def test_upload_page_loads(self):
        response = self.client.get(reverse("upload"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Load Planning Dataset")

    def test_lot_size_page_loads(self):
        response = self.client.get(reverse("lot_size"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Position Sizing")

    def test_risk_per_trade_page_loads(self):
        response = self.client.get(reverse("risk_per_trade"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trade Risk Controls")

    def test_strategy_risk_page_loads(self):
        response = self.client.get(reverse("strategy_risk"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Strategy Exposure Review")

    def test_sltp_page_loads(self):
        response = self.client.get(reverse("sltp"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SL / TP Planner")

    def test_simulation_history_page_loads(self):
        response = self.client.get(reverse("simulation_history"))
        self.assertEqual(response.status_code, 200)

    def test_lot_size_calculation(self):
        response = self.client.post(
            reverse("lot_size"),
            {"lot_size": "1.0", "pip_distance": "50", "pip_value": "10"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "500.00")

    def test_risk_per_trade_calculation(self):
        response = self.client.post(
            reverse("risk_per_trade"),
            {
                "account_balance": "10000",
                "lot_size": "1.0",
                "pip_value": "10",
                "stop_loss_pips": "30",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "300.00")

    def test_risk_per_trade_high_warning(self):
        response = self.client.post(
            reverse("risk_per_trade"),
            {
                "account_balance": "1000",
                "lot_size": "1.0",
                "pip_value": "10",
                "stop_loss_pips": "60",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Risk is high for a single trade and may expose the account to avoidable drawdown.",
        )


class UploadWorkflowTests(AuthenticatedUserMixin, TestCase):
    """Upload flow should load a planning dataset and expose dataset context."""

    def test_upload_dataset_redirects_to_dashboard_and_sets_session(self):
        response = self.upload_sample_dataset()

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Planning dataset loaded. 6 records are now available for baseline review and simulation.",
        )
        self.assertContains(response, "Planning Baseline")

        session = self.client.session
        self.assertIn(SESSION_DF_KEY, session)
        self.assertIn(SESSION_META_KEY, session)

        dataset_meta = session[SESSION_META_KEY]
        self.assertEqual(dataset_meta["filename"], "sample_trades.csv")
        self.assertEqual(dataset_meta["trade_count"], 6)

    def test_upload_dataset_shows_dataset_context_on_dashboard(self):
        response = self.upload_sample_dataset(name="baseline_reference.csv")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "baseline_reference.csv")
        self.assertContains(response, "6 records loaded")
        self.assertContains(response, "Planning Reference Only")

    def test_upload_invalid_file_extension_shows_error(self):
        bad_file = SimpleUploadedFile(
            "bad.txt",
            b"not,a,supported,file",
            content_type="text/plain",
        )
        response = self.client.post(reverse("upload"), {"file": bad_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unsupported file format")


class DatasetContextTests(AuthenticatedUserMixin, TestCase):
    """Dataset metadata should flow into key planning surfaces."""

    def test_dashboard_uses_uploaded_dataset_context(self):
        self.upload_sample_dataset(name="risk_context.csv")
        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "risk_context.csv")
        self.assertContains(response, "6 records loaded")
        self.assertContains(response, "Observed Risk Profile")

    def test_upload_page_shows_current_dataset_banner_after_upload(self):
        self.upload_sample_dataset(name="current_dataset.csv")
        response = self.client.get(reverse("upload"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current Dataset")
        self.assertContains(response, "current_dataset.csv")
        self.assertContains(response, "6 records")


class SimulationWorkflowTests(AuthenticatedUserMixin, TestCase):
    """Core simulation workflows should run end to end."""

    def test_simulation_run_smoke_creates_history_record(self):
        self.upload_sample_dataset()

        response = self.client.post(
            reverse("simulation_run"),
            {
                "num_simulations": "100",
                "num_trades": "5",
                "range_start": "0",
                "range_end": "6",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("result_list", response.context)
        self.assertTrue(response.context["result_list"])
        self.assertIn("equity_curve", response.context)
        self.assertTrue(response.context["equity_curve"])

        self.assertEqual(
            SimulationHistory.objects.filter(
                user=self.user,
                label="Stress-Test Run",
            ).count(),
            1,
        )

    def test_simulation_run_requires_uploaded_dataset(self):
        response = self.client.post(
            reverse("simulation_run"),
            {
                "num_simulations": "100",
                "num_trades": "5",
                "range_start": "0",
                "range_end": "6",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please load a planning dataset first.")

    def test_monte_carlo_smoke_returns_results(self):
        self.upload_sample_dataset()

        response = self.client.post(
            reverse("monte_carlo"),
            {
                "num_simulations": "120",
                "num_trades": "5",
                "range_start": "0",
                "range_end": "6",
                "session": "All",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("result_list", response.context)
        self.assertTrue(response.context["result_list"])
        self.assertContains(response, "Monte Carlo Lab")

    def test_simulation_scenario_smoke_returns_scenarios(self):
        self.upload_sample_dataset()

        response = self.client.post(
            reverse("simulation_scenario"),
            {
                "num_simulations_1": "100",
                "num_trades_1": "5",
                "range_start_1": "0",
                "range_end_1": "6",
                "start_date_1": "",
                "end_date_1": "",
                "num_simulations_2": "80",
                "num_trades_2": "4",
                "range_start_2": "0",
                "range_end_2": "6",
                "start_date_2": "",
                "end_date_2": "",
                "num_simulations_3": "",
                "num_trades_3": "",
                "range_start_3": "",
                "range_end_3": "",
                "start_date_3": "",
                "end_date_3": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("scenarios", response.context)
        self.assertGreaterEqual(len(response.context["scenarios"]), 2)


class ScreenshotManagementTests(AuthenticatedUserMixin, TestCase):
    """Screenshot upload/delete requires staff."""

    def test_non_staff_cannot_upload_screenshot(self):
        response = self.client.post(reverse("upload_screenshot"))
        self.assertEqual(response.status_code, 302)


class SimulationOwnershipTests(TestCase):
    """Users can only access their own simulations."""

    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="testpass123")
        self.user2 = User.objects.create_user(username="user2", password="testpass123")
        self.sim = SimulationHistory.objects.create(
            user=self.user1,
            label="User1 Sim",
            parameters={"test": True},
            results={"outcome": 100},
            chart_base64="",
        )

    def test_owner_can_view_detail(self):
        self.client.login(username="user1", password="testpass123")
        response = self.client.get(
            reverse("simulation_detail", kwargs={"pk": self.sim.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_view_detail(self):
        self.client.login(username="user2", password="testpass123")
        response = self.client.get(
            reverse("simulation_detail", kwargs={"pk": self.sim.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_other_user_cannot_delete(self):
        self.client.login(username="user2", password="testpass123")
        response = self.client.post(
            reverse("simulation_delete", kwargs={"pk": self.sim.pk})
        )
        self.assertEqual(response.status_code, 404)

    def test_owner_can_download_json(self):
        self.client.login(username="user1", password="testpass123")
        response = self.client.get(
            reverse("simulation_download_json", kwargs={"pk": self.sim.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_other_user_cannot_download_json(self):
        self.client.login(username="user2", password="testpass123")
        response = self.client.get(
            reverse("simulation_download_json", kwargs={"pk": self.sim.pk})
        )
        self.assertEqual(response.status_code, 404)


class ServiceLayerCalculationTests(TestCase):
    """Edge-case tests for core service functions."""

    def test_calculate_lot_size_returns_expected_values(self):
        result = calculate_lot_size(1.5, 20, 10)
        self.assertEqual(result["risk_per_pip"], 15.0)
        self.assertEqual(result["risk_amount"], 300.0)

    def test_calculate_lot_size_zero_distance_returns_zero_risk(self):
        result = calculate_lot_size(2, 0, 12)
        self.assertEqual(result["risk_per_pip"], 24.0)
        self.assertEqual(result["risk_amount"], 0.0)

    def test_calculate_trade_risk_returns_expected_values(self):
        result = calculate_trade_risk(10000, 1.5, 10, 20)
        self.assertEqual(result["risk_amount"], 300.0)
        self.assertEqual(result["risk_percent"], 3.0)

    def test_calculate_trade_risk_zero_balance_returns_zero_percent(self):
        result = calculate_trade_risk(0, 1, 10, 50)
        self.assertEqual(result["risk_amount"], 500.0)
        self.assertEqual(result["risk_percent"], 0.0)

    def test_build_trade_risk_warning_covers_all_thresholds(self):
        self.assertIn("conservative", build_trade_risk_warning(0.5))
        self.assertIn("controlled", build_trade_risk_warning(1.5))
        self.assertIn("elevated", build_trade_risk_warning(2.5))
        self.assertIn("high", build_trade_risk_warning(4.0))

    def test_calculate_strategy_risk_negative_expectancy_reduces_lot(self):
        result = calculate_strategy_risk(base_lot=2, win_rate=30, rr=1, volatility=1)
        self.assertLess(result["recommended_lot"], 2.0)
        self.assertIn("Negative expectancy", result["stance"])

    def test_calculate_strategy_risk_positive_expectancy_labels_baseline(self):
        result = calculate_strategy_risk(base_lot=2, win_rate=60, rr=2, volatility=1)
        self.assertGreater(result["recommended_lot"], 2.0)
        self.assertIn("Positive expectancy", result["stance"])

    def test_calculate_sltp_returns_expected_ratio_and_amounts(self):
        result = calculate_sltp(entry=1200, stop_loss=1000, take_profit=1500, lot_size=2, pip_value=10)
        self.assertEqual(result["risk_pips"], 200.0)
        self.assertEqual(result["reward_pips"], 300.0)
        self.assertEqual(result["rr_ratio"], 1.5)
        self.assertEqual(result["risk_amount"], 4000.0)
        self.assertEqual(result["reward_amount"], 6000.0)

    def test_run_simulation_include_curves_returns_expected_keys(self):
        np.random.seed(42)
        result = run_simulation([50, -20, 40, -10, 30], num_simulations=25, num_trades=4, include_curves=True)
        self.assertIn("min", result)
        self.assertIn("median", result)
        self.assertIn("p95", result)
        self.assertIn("prob_positive", result)
        self.assertIn("equity_curves", result)
        self.assertEqual(len(result["equity_curves"]), 25)

    def test_run_simulation_rejects_empty_input(self):
        with self.assertRaises(ValueError):
            run_simulation([], num_simulations=10, num_trades=3)

    def test_build_simulation_warning_small_sample(self):
        warning = build_simulation_warning(sample_size=5, num_simulations=1000, num_trades=20)
        self.assertIn("very small", warning)

    def test_build_simulation_warning_large_trade_request(self):
        warning = build_simulation_warning(sample_size=10, num_simulations=1000, num_trades=100)
        self.assertIn("large relative to the filtered sample", warning)

    def test_build_simulation_warning_low_simulation_count(self):
        warning = build_simulation_warning(sample_size=50, num_simulations=50, num_trades=10)
        self.assertIn("low number of simulations", warning)

    def test_build_dashboard_interpretation_fragile_edge(self):
        df = pd.DataFrame({"profit": [10, -20, 5, -15]})
        result = build_dashboard_interpretation(df=df, max_drawdown=30, volatility=12, profit_factor=0.8)
        self.assertIn("fragile", result["primary_downside_concern"].lower())

    def test_build_dashboard_interpretation_drawdown_branch(self):
        df = pd.DataFrame({"profit": [100, -80, 95, -70, 110, -60]})
        result = build_dashboard_interpretation(df=df, max_drawdown=500, volatility=80, profit_factor=1.4)
        self.assertIn("drawdown depth", result["primary_downside_concern"].lower())

    def test_build_dashboard_interpretation_high_volatility_branch(self):
        df = pd.DataFrame({"profit": [10, -1, 10, -1, 10, -1]})
        result = build_dashboard_interpretation(df=df, max_drawdown=2, volatility=9, profit_factor=2.0)
        self.assertIn("dispersion", result["primary_downside_concern"].lower())


class IngestionServiceTests(AuthenticatedUserMixin, TestCase):
    """Ingestion and session dataset helper tests."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def test_prepare_trade_import_dataframe_normalises_aliases(self):
        file_obj = build_csv_file(
            name="alias_data.csv",
            content=(
                "open_time,instrument,volume,entry,pnl,market_session\n"
                "2024-01-02 09:00:00,EURUSD,1,1.1000,50,London\n"
                "2024-01-01 02:00:00,GBPUSD,1,1.2000,-20,Asia\n"
            ),
        )
        df = prepare_trade_import_dataframe(file_obj)

        self.assertIn("date", df.columns)
        self.assertIn("profit", df.columns)
        self.assertIn("session", df.columns)
        self.assertIn("symbol", df.columns)
        self.assertEqual(df.iloc[0]["symbol"], "GBPUSD")
        self.assertEqual(df.iloc[0]["profit"], -20)

    def test_prepare_trade_import_dataframe_rejects_missing_profit_column(self):
        bad_file = build_csv_file(
            name="missing_profit.csv",
            content=(
                "date,symbol,volume,entryprice,exitprice\n"
                "2024-01-01,EURUSD,1,1.1000,1.1050\n"
            ),
        )
        with self.assertRaises(ValueError):
            prepare_trade_import_dataframe(bad_file)

    def test_prepare_simulation_dataframe_sorts_by_date(self):
        file_obj = build_csv_file(
            name="unsorted_sample.csv",
            content=(
                "date,symbol,volume,entryprice,exitprice,profit\n"
                "2024-01-03,EURUSD,1,1.1000,1.1050,30\n"
                "2024-01-01,EURUSD,1,1.1000,1.0950,-20\n"
                "2024-01-02,EURUSD,1,1.0950,1.1100,40\n"
            ),
        )
        df = prepare_simulation_dataframe(file_obj)
        self.assertEqual(str(df.iloc[0]["date"].date()), "2024-01-01")
        self.assertEqual(str(df.iloc[-1]["date"].date()), "2024-01-03")

    def test_session_dataset_round_trip_save_load_and_clear(self):
        request = attach_session(self.factory.get("/"))
        request.user = self.user

        df = prepare_trade_import_dataframe(build_csv_file())
        save_uploaded_df_to_session(request, df)
        save_dataset_meta_to_session(request, "session_roundtrip.csv", df)

        loaded_df = load_uploaded_df_from_session(request)
        loaded_meta = load_dataset_meta_from_session(request)

        self.assertIsNotNone(loaded_df)
        self.assertEqual(len(loaded_df), 6)
        self.assertEqual(loaded_meta["filename"], "session_roundtrip.csv")

        clear_uploaded_dataset_from_session(request)
        self.assertIsNone(load_uploaded_df_from_session(request))
        self.assertIsNone(load_dataset_meta_from_session(request))

    def test_get_active_planning_df_prefers_session_dataset(self):
        request = attach_session(self.factory.get("/"))
        request.user = self.user

        df = prepare_trade_import_dataframe(build_csv_file(name="planning_source.csv"))
        save_uploaded_df_to_session(request, df)
        save_dataset_meta_to_session(request, "planning_source.csv", df)

        active_df, dataset_meta = get_active_planning_df(request)

        self.assertIsNotNone(active_df)
        self.assertEqual(len(active_df), 6)
        self.assertEqual(dataset_meta["filename"], "planning_source.csv")


class HistoryWorkflowIntegrationTests(AuthenticatedUserMixin, TestCase):
    """Saved-run integration flows should work end to end."""

    def create_saved_run(self):
        self.upload_sample_dataset()
        response = self.client.post(
            reverse("simulation_run"),
            {
                "num_simulations": "100",
                "num_trades": "5",
                "range_start": "0",
                "range_end": "6",
            },
        )
        self.assertEqual(response.status_code, 200)
        return SimulationHistory.objects.filter(user=self.user).latest("created_at")

    def test_history_page_shows_saved_run(self):
        self.create_saved_run()
        response = self.client.get(reverse("simulation_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stress-Test Run")

    def test_simulation_detail_page_renders_saved_run(self):
        sim = self.create_saved_run()
        response = self.client.get(reverse("simulation_detail", kwargs={"pk": sim.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Stress-Test Run")
        self.assertContains(response, "Executive Summary")

    def test_owner_can_delete_saved_run_end_to_end(self):
        sim = self.create_saved_run()
        response = self.client.post(reverse("simulation_delete", kwargs={"pk": sim.pk}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(SimulationHistory.objects.filter(pk=sim.pk).exists())

    def test_monte_carlo_shows_no_results_message_for_impossible_date_filter(self):
        self.upload_sample_dataset()
        response = self.client.post(
            reverse("monte_carlo"),
            {
                "num_simulations": "100",
                "num_trades": "5",
                "range_start": "0",
                "range_end": "6",
                "session": "All",
                "start_date": "2030-01-01",
                "end_date": "2030-01-05",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No records matched your current filters.")

    def test_scenario_view_sets_best_scenario_context(self):
        self.upload_sample_dataset()
        response = self.client.post(
            reverse("simulation_scenario"),
            {
                "num_simulations_1": "100",
                "num_trades_1": "5",
                "range_start_1": "0",
                "range_end_1": "6",
                "start_date_1": "",
                "end_date_1": "",
                "num_simulations_2": "80",
                "num_trades_2": "4",
                "range_start_2": "0",
                "range_end_2": "6",
                "start_date_2": "",
                "end_date_2": "",
                "num_simulations_3": "",
                "num_trades_3": "",
                "range_start_3": "",
                "range_end_3": "",
                "start_date_3": "",
                "end_date_3": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("best_scenario", response.context)
        self.assertIsNotNone(response.context["best_scenario"])

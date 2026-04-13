from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from .services import SESSION_DF_KEY, SESSION_META_KEY
from .models import SimulationHistory

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
        self.assertContains(response, "Capital Preservation Dashboard")

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
                label="Stress-Test Plan",
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
        self.assertContains(response, "Monte Carlo Risk Simulation")

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
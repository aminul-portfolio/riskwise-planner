from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


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


class AuthenticatedPageTests(TestCase):
    """Pages that require login return correctly for authenticated users."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

    def test_dashboard_no_data(self):
        """Dashboard shows empty-state message when no trades are uploaded."""
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No risk plan loaded yet")

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
        """Lot size calculator returns a valid result."""
        response = self.client.post(
            reverse("lot_size"),
            {"lot_size": "1.0", "pip_distance": "50", "pip_value": "10"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "500.00")

    def test_risk_per_trade_calculation(self):
        """Risk-per-trade shows correct risk amount."""
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
        """High-risk trade triggers an elevated/high warning."""
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
        # 60% risk should trigger high warning
        self.assertContains(response, "Review Before Use")


class ScreenshotManagementTests(TestCase):
    """Screenshot upload/delete requires staff."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="normaluser", password="testpass123"
        )
        self.client = Client()
        self.client.login(username="normaluser", password="testpass123")

    def test_non_staff_cannot_upload_screenshot(self):
        response = self.client.post(reverse("upload_screenshot"))
        self.assertEqual(response.status_code, 302)


class SimulationOwnershipTests(TestCase):
    """Users can only access their own simulations."""

    def setUp(self):
        from riskwise.models import SimulationHistory

        self.user1 = User.objects.create_user(
            username="user1", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2", password="testpass123"
        )
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

from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("upload/", views.upload_file, name="upload"),
    path("dashboard/", views.dashboard, name="dashboard"),

    path("calculators/lot-size/", views.lot_size_calculator, name="lot_size"),
    path("calculators/risk-per-trade/", views.risk_per_trade_calculator, name="risk_per_trade"),
    path("calculators/strategy-risk/", views.strategy_risk_calculator, name="strategy_risk"),
    path("calculators/sltp/", views.sltp_calculator, name="sltp"),

    path("simulations/monte-carlo/", views.monte_carlo_simulation, name="monte_carlo"),
    path("simulations/run/", views.simulation_run_view, name="simulation_run"),
    path("simulations/scenario/", views.simulation_scenario_view, name="simulation_scenario"),
    path("simulations/history/", views.simulation_history_view, name="simulation_history"),

    path("simulations/<int:pk>/download/json/", views.simulation_download_json_view, name="simulation_download_json"),
    path("simulations/<int:pk>/download/chart/", views.simulation_download_chart_view, name="simulation_download_chart"),
    path("simulations/<int:pk>/delete/", views.simulation_delete_view, name="simulation_delete"),
    path("simulations/<int:pk>/", views.simulation_detail_view, name="simulation_detail"),

    path("upload-screenshot/", views.upload_screenshot, name="upload_screenshot"),
    path("delete-screenshot/<int:pk>/", views.delete_screenshot, name="delete_screenshot"),

    path("login/", auth_views.LoginView.as_view(template_name="riskwise/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
]
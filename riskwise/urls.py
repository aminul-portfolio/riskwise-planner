from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    home,
    upload_file,
    dashboard,
    lot_size_calculator,
    risk_per_trade_calculator,
    strategy_risk_calculator,
    sltp_calculator,
    monte_carlo_simulation,
    simulation_run_view,
    simulation_scenario_view,
    simulation_history_view,
    simulation_download_json_view,
    simulation_download_chart_view,
    simulation_delete_view,
    simulation_detail_view,
    upload_screenshot,
    delete_screenshot,
)

urlpatterns = [
    path("", home, name="home"),
    path("upload/", upload_file, name="upload"),
    path("dashboard/", dashboard, name="dashboard"),

    path("calculators/lot-size/", lot_size_calculator, name="lot_size"),
    path("calculators/risk-per-trade/", risk_per_trade_calculator, name="risk_per_trade"),
    path("calculators/strategy-risk/", strategy_risk_calculator, name="strategy_risk"),
    path("calculators/sltp/", sltp_calculator, name="sltp"),

    path("simulations/monte-carlo/", monte_carlo_simulation, name="monte_carlo"),
    path("simulations/run/", simulation_run_view, name="simulation_run"),
    path("simulations/scenario/", simulation_scenario_view, name="simulation_scenario"),
    path("simulations/history/", simulation_history_view, name="simulation_history"),

    path("simulations/<int:pk>/download/json/", simulation_download_json_view, name="simulation_download_json"),
    path("simulations/<int:pk>/download/chart/", simulation_download_chart_view, name="simulation_download_chart"),
    path("simulations/<int:pk>/delete/", simulation_delete_view, name="simulation_delete"),
    path("simulations/<int:pk>/", simulation_detail_view, name="simulation_detail"),

    path("upload-screenshot/", upload_screenshot, name="upload_screenshot"),
    path("delete-screenshot/<int:pk>/", delete_screenshot, name="delete_screenshot"),

    path("login/", auth_views.LoginView.as_view(template_name="riskwise/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
]
from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.home, name="home"),
    # +++ ADD THIS NEW LINE FOR THE AJAX ENDPOINT +++
    path("dashboard-data/", views.dashboard_data, name="dashboard_data"),
    path("predict-stock/", views.predict_stock, name="predict_stock"),
    path('stocks/', views.stocks_view, name='stocks'), 
    path("register/", views.register, name="register"),
    path("verify-registration-otp/", views.verify_registration_otp, name="verify_registration_otp"),
    path("login/", views.login_view, name="login"),
    path("verify-login-otp/", views.verify_login_otp, name="verify_login_otp"),
    path('logout/', views.logout_view, name='logout'),
]

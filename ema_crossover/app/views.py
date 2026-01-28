from django.http import JsonResponse
from django.contrib.auth import authenticate, login, get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .forms import RegistrationForm, LoginForm
from .utils import generate_otp, get_stored_otp, increment_attempts, attempts_left, delete_otp, send_otp_email
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

User = get_user_model()


# --------------------
# Registration Step 1 - Send OTP
# --------------------
@csrf_exempt
def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if not form.is_valid():
            return JsonResponse({"status": "error", "errors": form.errors})

        email = form.cleaned_data["email"].lower()

        if User.objects.filter(email=email).exists():
            return JsonResponse({"status": "error", "message": "Email already registered"})

        otp = generate_otp(email)
        send_otp_email(email, otp, purpose="registration")

        # Save pending registration in session
        request.session["pending_registration"] = {
            "first_name": form.cleaned_data["first_name"],
            "last_name": form.cleaned_data["last_name"],
            "email": email,
            "password": form.cleaned_data["password"],
        }
        return JsonResponse({"status": "otp_sent", "message": "OTP sent to your email", "email": email})

    # Handle GET -> render registration form
    form = RegistrationForm()
    return render(request, "register.html", {"form": form})


# --------------------
# Registration Step 2 - Verify OTP
# --------------------
@csrf_exempt
def verify_registration_otp(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    email = request.POST.get("email", "").lower()
    otp = request.POST.get("otp", "")

    pending = request.session.get("pending_registration")
    if not pending or pending["email"] != email:
        return JsonResponse({"status": "error", "message": "No pending registration"})

    stored = get_stored_otp(email)
    if stored is None:
        return JsonResponse({"status": "error", "message": "OTP expired"})

    if stored != otp:
        increment_attempts(email)
        return JsonResponse({
            "status": "error",
            "message": "Invalid OTP",
            "attempts_left": attempts_left(email)
        })

    # Create user
    user = User.objects.create_user(
        email=email,
        username=email,  # if using default User model
        first_name=pending["first_name"],
        last_name=pending["last_name"],
        password=pending["password"]
    )
    delete_otp(email)
    del request.session["pending_registration"]

    return JsonResponse({"status": "success", "message": "Registration successful"})


# --------------------
# Login Step 1 - Send OTP
# --------------------
@csrf_exempt
def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if not form.is_valid():
            return JsonResponse({"status": "error", "errors": form.errors})

        email = form.cleaned_data["email"].lower()
        password = form.cleaned_data["password"]

        user = authenticate(request, username=email, password=password)
        if not user:
            return JsonResponse({"status": "error", "message": "Invalid credentials"})

        otp = generate_otp(email)
        send_otp_email(email, otp, purpose="login")

        request.session["pending_login"] = {"user_id": user.id, "email": email}

        return JsonResponse({"status": "otp_sent", "message": "OTP sent to your email", "email": email})

    # GET request → render login form
    form = LoginForm()
    return render(request, "login.html", {"form": form})


# --------------------
# Login Step 2 - Verify OTP
# --------------------
@csrf_exempt
def verify_login_otp(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

    email = request.POST.get("email", "").lower()
    otp = request.POST.get("otp", "")

    pending = request.session.get("pending_login")
    if not pending or pending["email"] != email:
        return JsonResponse({"status": "error", "message": "No pending login"})

    stored = get_stored_otp(email)
    if stored is None:
        return JsonResponse({"status": "error", "message": "OTP expired"})

    if stored != otp:
        increment_attempts(email)
        return JsonResponse({
            "status": "error",
            "message": "Invalid OTP",
            "attempts_left": attempts_left(email)
        })

    # OTP valid → login
    user = User.objects.get(pk=pending["user_id"])
    login(request, user)
    delete_otp(email)
    del request.session["pending_login"]

    return JsonResponse({"status": "success", "message": "Login successful"})


# --------------------
# Home Page (Updated Logic)
# --------------------
from django.shortcuts import render, redirect
from django.conf import settings
import os
import subprocess
import sys
# NEW IMPORTS FOR AJAX
from django.http import JsonResponse
from django.template.defaultfilters import timesince

from .services import load_tickers_from_csv, TIMEFRAME_OPTIONS
from .models import MonitoringSession, MonitoredStock, SignalEvent



BACKGROUND_PROCESS = None

def home(request):
    global BACKGROUND_PROCESS
    
    active_session = MonitoringSession.objects.filter(is_active=True).first()
    context = {}

    # ===============================
    # EXISTING DASHBOARD LOGIC
    # ===============================
    if active_session:
        monitored_stocks = active_session.stocks.all().order_by('ticker')
        total_stocks = len(monitored_stocks)
        
        bullish_count = monitored_stocks.filter(last_trend__icontains='BULLISH').count()
        bearish_count = monitored_stocks.filter(last_trend__icontains='BEARISH').count()
        neutral_count = total_stocks - bullish_count - bearish_count
        
        bullish_percentage = int((bullish_count / total_stocks) * 100) if total_stocks > 0 else 0
        bearish_percentage = int((bearish_count / total_stocks) * 100) if total_stocks > 0 else 0
        neutral_percentage = 100 - bullish_percentage - bearish_percentage if total_stocks > 0 else 0
        
        recent_signals = active_session.signals.all().order_by('-timestamp')[:5]

        context.update({
            'is_running': True,
            'active_session': active_session,
            'monitored_stocks': monitored_stocks,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
            'bullish_percentage': bullish_percentage,
            'bearish_percentage': bearish_percentage,
            'neutral_percentage': neutral_percentage,
            'recent_signals': recent_signals,
        })
    else:
        context['is_running'] = False

    # ===============================
    # EXISTING STOCK BOT DATA
    # ===============================
    csv_file_path = os.path.join(settings.BASE_DIR, 'app', 'stock_names.csv')
    context['all_tickers'] = load_tickers_from_csv(csv_file_path)
    context['timeframes'] = TIMEFRAME_OPTIONS.keys()

    # ===============================
    # 🔥 NEW: PREDICTION CSV FILE LOGIC
    # ===============================
    prediction_dir = os.path.join(
        settings.BASE_DIR,
        'app',
        'stock_data_5_years'
    )

    if os.path.exists(prediction_dir):
        prediction_stocks = [
            f.replace('.csv', '')
            for f in os.listdir(prediction_dir)
            if f.endswith('.csv')
        ]
    else:
        prediction_stocks = []

    context['prediction_stocks'] = sorted(prediction_stocks)

    # ===============================
    # EXISTING POST ACTION LOGIC
    # ===============================
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'start':
            if BACKGROUND_PROCESS and BACKGROUND_PROCESS.poll() is None:
                BACKGROUND_PROCESS.terminate()
            MonitoringSession.objects.all().delete()
            
            selected_tickers = request.POST.getlist('tickers')
            selected_timeframes = request.POST.getlist('timeframes')

            if not selected_tickers or len(selected_tickers) != len(selected_timeframes):
                context['error'] = "An error occurred. Please ensure every stock has a timeframe."
                return render(request, "home.html", context)

            session = MonitoringSession.objects.create(is_active=True, timeframe="Multiple")
            
            stock_pairs_for_command = []
            
            for ticker, timeframe in zip(selected_tickers, selected_timeframes):
                if ticker and timeframe:
                    MonitoredStock.objects.create(session=session, ticker=ticker, timeframe=timeframe)
                    stock_pairs_for_command.append(f"{ticker}:{timeframe}")

            if not stock_pairs_for_command:
                context['error'] = "No valid stock and timeframe pairs were selected."
                return render(request, "home.html", context)

            pairs_str = ",".join(stock_pairs_for_command)
            command = [sys.executable, 'manage.py', 'run_stock_bot', '--pairs', pairs_str]
            
            BACKGROUND_PROCESS = subprocess.Popen(command)
            return redirect('home')

        elif action == 'stop':
            if BACKGROUND_PROCESS and BACKGROUND_PROCESS.poll() is None:
                BACKGROUND_PROCESS.terminate()
                BACKGROUND_PROCESS = None
            MonitoringSession.objects.filter(is_active=True).delete()
            return redirect('home')

    return render(request, 'home.html', context)



# +++ NEW FUNCTION FOR AJAX POLLING +++
def dashboard_data(request):
    """
    This view provides the dashboard data as a JSON response for AJAX calls.
    """
    data = {'is_running': False}
    active_session = MonitoringSession.objects.filter(is_active=True).first()

    if active_session:
        monitored_stocks_qs = active_session.stocks.all().order_by('ticker')
        total_stocks = monitored_stocks_qs.count()

        bullish_count = monitored_stocks_qs.filter(last_trend__icontains='BULLISH').count()
        bearish_count = monitored_stocks_qs.filter(last_trend__icontains='BEARISH').count()
        neutral_count = total_stocks - bullish_count - bearish_count

        bullish_percentage = int((bullish_count / total_stocks) * 100) if total_stocks > 0 else 0
        bearish_percentage = int((bearish_count / total_stocks) * 100) if total_stocks > 0 else 0
        neutral_percentage = 100 - bullish_percentage - bearish_percentage if total_stocks > 0 else 0
        
        recent_signals_qs = active_session.signals.all().order_by('-timestamp')[:5]

        # Prepare data for JSON serialization
        monitored_stocks_data = [
            {
                'ticker': stock.ticker,
                'timeframe': stock.timeframe,
                'last_trend': stock.last_trend or "Waiting...",
                'last_price': f"{stock.last_price:.2f}" if stock.last_price is not None else "N/A",
                'last_updated': f"{timesince(stock.last_updated)} ago"
            }
            for stock in monitored_stocks_qs
        ]

        recent_signals_data = [
            {
                'ticker': signal.ticker,
                'signal_type': signal.signal_type,
                'timestamp': f"{timesince(signal.timestamp)} ago",
                'is_bullish': 'BULLISH' in signal.signal_type
            }
            for signal in recent_signals_qs
        ]
        
        data.update({
            'is_running': True,
            'bullish_count': bullish_count,
            'bearish_count': bearish_count,
            'neutral_count': neutral_count,
            'total_stocks': total_stocks,
            'bullish_percentage': bullish_percentage,
            'bearish_percentage': bearish_percentage,
            'neutral_percentage': neutral_percentage,
            'recent_signals_count': recent_signals_qs.count(),
            'monitored_stocks': monitored_stocks_data,
            'recent_signals': recent_signals_data,
        })

    return JsonResponse(data)

from django.views.decorators.http import require_POST
from .ml.train_and_predict import train_and_predict_stock


@require_POST
@login_required
def predict_stock(request):
    stock = request.POST.get('stock')
    timeframe = request.POST.get('timeframe')  # optional, future use

    if not stock:
        return JsonResponse({"error": "Stock not selected"}, status=400)

    csv_path = os.path.join(
        settings.BASE_DIR,
        'app',
        'stock_data_5_years',
        f'{stock}.csv'
    )

    if not os.path.exists(csv_path):
        return JsonResponse({"error": "CSV file not found"}, status=404)

    try:
        result = train_and_predict_stock(csv_path)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({
        "trend": result["trend"],
        "confidence": result["confidence"],
        "action": result["action"],
        "metrics": result["metrics"],
        "chart_data": result["chart_data"],
    })



def stocks_view(request):
    return render(request, 'stocks.html')

# --------------------
# index Page
# --------------------
def index(request):
    return render(request, "index.html") 

def logout_view(request):
    logout(request)
    return redirect('index')  # Redirect to home or login page
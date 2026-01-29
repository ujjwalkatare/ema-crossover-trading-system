📈 Real-Time EMA Crossover Stock Monitoring & Prediction System
A full-stack Django-based real-time stock analysis system that monitors live market data, detects EMA crossovers, provides live dashboard analytics, and predicts future stock trends using machine learning.
This project is designed to demonstrate real-time system design, background processing, secure authentication, and data-driven decision support, making it suitable for academic projects, portfolios, and interviews.


🚀 Key Features

🔐 OTP-Based Secure Authentication
Two-step registration and login using email OTP
Prevents unauthorized access and fake accounts

📈 Real-Time EMA Crossover Detection
Calculates fast and slow EMAs
Detects bullish and bearish crossover signals
Supports multiple timeframes

⏱ Multi-Timeframe Stock Monitoring
15 minutes
30 minutes
1 hour
4 hour

🤖 Background Stock Monitoring Bot
Runs independently of the web server
Fetches live market data using APIs
Continuously analyzes selected stocks

📊 Live Interactive Dashboard
Real-time updates using AJAX
Displays bullish, bearish, and neutral stock counts
Shows recent EMA signals with timestamps
Market sentiment visualization

🧠 Machine Learning-Based Stock Prediction
Uses historical stock data stored in CSV files
Trains a model on past price movements
Predicts future trend, confidence score, and suggested action (BUY / SELL / HOLD)

📁 CSV-Based Data Management
Stock symbols loaded dynamically from CSV
Historical OHLC data used for ML training

🧩 How the System Works
![ChatGPT Image Jan 29, 2026, 11_00_33 AM](https://github.com/user-attachments/assets/616f96bb-7079-49dd-a661-e796e55cf684)
User logs in using OTP-based authentication
User selects stocks and assigns timeframes
A monitoring session is created
A background bot:
Fetches live stock prices
Calculates EMA values
Detects crossover events
Signals are stored in the database
Dashboard updates live using AJAX
User can run AI-based predictions using historical CSV data

🛠 Tech Stack
Backend
Python
Django
Django ORM

Frontend
HTML
CSS
JavaScript
AJAX

Database
SQLite (development)
Machine Learning
Pandas
NumPy
Scikit-learn

Other Tools
Git & GitHub
VS Code
REST APIs (Stock Market Data, Email OTP)

⭐ Why This Project Matters

This project demonstrates:
Real-time data processing
Secure authentication design
Background task execution
Clean Django architecture
Practical use of machine learning in finance

👤 Author

Ujjwal
GitHub: https://github.com/ujjwalkatare

🎥 Project Demo

📽 Demo video and screenshots are available on LinkedIn
🔗 GitHub repository contains full source code

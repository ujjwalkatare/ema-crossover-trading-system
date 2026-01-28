class StocksAnalysis {
  constructor() {
    this.stocks = [];
    this.filteredStocks = [];
    this.currentChart = null;
    this.init();
  }

  init() {
    this.loadStocksData();
    this.initEventListeners();
  }

  async loadStocksData() {
    try {
      // Simulate API call - replace with actual endpoint
      const response = await this.fetchStocksData();
      this.stocks = response;
      this.filteredStocks = response;
      this.renderStocksGrid();
      this.hideLoadingSpinner();
    } catch (error) {
      console.error("Error loading stocks data:", error);
      this.showError("Failed to load stocks data");
    }
  }

  async fetchStocksData() {
    // Simulate API response - replace with actual API call
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve([
          {
            symbol: "AAPL",
            name: "Apple Inc.",
            price: 182.63,
            change: 1.24,
            changePercent: 0.68,
            ema20: 180.45,
            ema50: 178.92,
            ema200: 175.34,
            signal: "bullish",
            sector: "technology",
            volume: 45678900,
            marketCap: "2.87T",
          },
          {
            symbol: "MSFT",
            name: "Microsoft Corporation",
            price: 374.58,
            change: -2.34,
            changePercent: -0.62,
            ema20: 372.15,
            ema50: 368.92,
            ema200: 355.67,
            signal: "neutral",
            sector: "technology",
            volume: 23456700,
            marketCap: "2.78T",
          },
          {
            symbol: "GOOGL",
            name: "Alphabet Inc.",
            price: 138.21,
            change: 0.89,
            changePercent: 0.65,
            ema20: 136.45,
            ema50: 134.78,
            ema200: 128.92,
            signal: "bullish",
            sector: "technology",
            volume: 34567800,
            marketCap: "1.75T",
          },
          {
            symbol: "TSLA",
            name: "Tesla Inc.",
            price: 248.42,
            change: -5.67,
            changePercent: -2.23,
            ema20: 252.34,
            ema50: 245.67,
            ema200: 238.45,
            signal: "bearish",
            sector: "automotive",
            volume: 56789000,
            marketCap: "789.45B",
          },
          {
            symbol: "AMZN",
            name: "Amazon.com Inc.",
            price: 154.67,
            change: 1.23,
            changePercent: 0.8,
            ema20: 152.89,
            ema50: 149.34,
            ema200: 142.56,
            signal: "bullish",
            sector: "consumer",
            volume: 45678900,
            marketCap: "1.59T",
          },
          {
            symbol: "META",
            name: "Meta Platforms Inc.",
            price: 346.89,
            change: 3.45,
            changePercent: 1.0,
            ema20: 342.15,
            ema50: 338.67,
            ema200: 325.89,
            signal: "bullish",
            sector: "technology",
            volume: 23456700,
            marketCap: "889.34B",
          },
        ]);
      }, 1000);
    });
  }

  renderStocksGrid() {
    const grid = document.getElementById("stocksGrid");

    if (this.filteredStocks.length === 0) {
      grid.innerHTML = `
        <div class="col-12 text-center py-5">
          <i class="bi bi-search display-1 text-muted"></i>
          <h4 class="mt-3 text-muted">No stocks found</h4>
          <p class="text-muted">Try adjusting your search or filters</p>
        </div>
      `;
      return;
    }

    grid.innerHTML = this.filteredStocks
      .map(
        (stock) => `
      <div class="col-xl-4 col-lg-6 col-md-6">
        <div class="stock-card" data-symbol="${stock.symbol}">
          <div class="stock-header">
            <div>
              <h3 class="stock-symbol">${stock.symbol}</h3>
              <p class="stock-name">${stock.name}</p>
            </div>
            <span class="signal-badge signal-${stock.signal}">
              ${stock.signal}
            </span>
          </div>
          
          <div class="stock-price">$${stock.price.toFixed(2)}</div>
          <span class="stock-change ${
            stock.change >= 0 ? "positive" : "negative"
          }">
            ${stock.change >= 0 ? "+" : ""}${stock.change.toFixed(
          2
        )} (${stock.changePercent.toFixed(2)}%)
          </span>
          
          <div class="ema-indicators">
            <div class="ema-indicator">
              <div class="ema-label">EMA 20</div>
              <div class="ema-value">$${stock.ema20.toFixed(2)}</div>
            </div>
            <div class="ema-indicator">
              <div class="ema-label">EMA 50</div>
              <div class="ema-value">$${stock.ema50.toFixed(2)}</div>
            </div>
            <div class="ema-indicator">
              <div class="ema-label">EMA 200</div>
              <div class="ema-value">$${stock.ema200.toFixed(2)}</div>
            </div>
            <div class="ema-indicator">
              <div class="ema-label">Signal</div>
              <div class="ema-value ${this.getSignalColor(stock)}">
                ${this.getSignalText(stock)}
              </div>
            </div>
          </div>
          
          <div class="stock-chart-mini">
            <small>Click to view detailed analysis</small>
          </div>
          
          <div class="d-flex justify-content-between text-muted small">
            <span>Volume: ${this.formatNumber(stock.volume)}</span>
            <span>Mkt Cap: ${stock.marketCap}</span>
          </div>
        </div>
      </div>
    `
      )
      .join("");

    this.attachStockCardEvents();
  }

  getSignalColor(stock) {
    if (stock.price > stock.ema20 && stock.ema20 > stock.ema50)
      return "text-success";
    if (stock.price < stock.ema20 && stock.ema20 < stock.ema50)
      return "text-danger";
    return "text-warning";
  }

  getSignalText(stock) {
    if (stock.price > stock.ema20 && stock.ema20 > stock.ema50)
      return "Bullish";
    if (stock.price < stock.ema20 && stock.ema20 < stock.ema50)
      return "Bearish";
    return "Neutral";
  }

  attachStockCardEvents() {
    document.querySelectorAll(".stock-card").forEach((card) => {
      card.addEventListener("click", () => {
        const symbol = card.dataset.symbol;
        this.showStockAnalysis(symbol);
      });
    });
  }

  showStockAnalysis(symbol) {
    const stock = this.stocks.find((s) => s.symbol === symbol);
    if (!stock) return;

    const modal = new bootstrap.Modal(document.getElementById("chartModal"));
    document.getElementById(
      "chartModalTitle"
    ).textContent = `${stock.symbol} - ${stock.name} Analysis`;

    this.renderStockChart(stock);
    modal.show();
  }

  renderStockChart(stock) {
    const ctx = document.getElementById("chartContainer");

    if (this.currentChart) {
      this.currentChart.destroy();
    }

    // Simulate chart data - replace with actual data
    const dates = Array.from({ length: 30 }, (_, i) => {
      const date = new Date();
      date.setDate(date.getDate() - (29 - i));
      return date.toLocaleDateString();
    });

    const prices = Array.from({ length: 30 }, (_, i) => {
      const basePrice = stock.price * 0.9;
      const variation = Math.sin(i * 0.3) * stock.price * 0.1;
      return basePrice + variation;
    });

    this.currentChart = new Chart(ctx, {
      type: "line",
      data: {
        labels: dates,
        datasets: [
          {
            label: "Price",
            data: prices,
            borderColor: "#0d6efd",
            backgroundColor: "rgba(13, 110, 253, 0.1)",
            tension: 0.4,
            fill: true,
          },
          {
            label: "EMA 20",
            data: prices.map(
              (_, i) => stock.ema20 * (1 + Math.sin(i * 0.3) * 0.05)
            ),
            borderColor: "#ff6b6b",
            borderDash: [5, 5],
            tension: 0.4,
          },
          {
            label: "EMA 50",
            data: prices.map(
              (_, i) => stock.ema50 * (1 + Math.sin(i * 0.2) * 0.03)
            ),
            borderColor: "#51cf66",
            borderDash: [5, 5],
            tension: 0.4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: {
            display: true,
            text: `EMA Crossover Analysis - ${stock.symbol}`,
          },
          tooltip: {
            mode: "index",
            intersect: false,
          },
        },
        scales: {
          x: {
            grid: {
              display: false,
            },
          },
          y: {
            beginAtZero: false,
          },
        },
      },
    });
  }

  initEventListeners() {
    // Search functionality
    document.getElementById("stockSearch").addEventListener("input", (e) => {
      this.filterStocks();
    });

    // Filter functionality
    document.getElementById("sectorFilter").addEventListener("change", (e) => {
      this.filterStocks();
    });

    document.getElementById("signalFilter").addEventListener("change", (e) => {
      this.filterStocks();
    });
  }

  filterStocks() {
    const searchTerm = document
      .getElementById("stockSearch")
      .value.toLowerCase();
    const sectorFilter = document.getElementById("sectorFilter").value;
    const signalFilter = document.getElementById("signalFilter").value;

    this.filteredStocks = this.stocks.filter((stock) => {
      const matchesSearch =
        stock.symbol.toLowerCase().includes(searchTerm) ||
        stock.name.toLowerCase().includes(searchTerm);
      const matchesSector = !sectorFilter || stock.sector === sectorFilter;
      const matchesSignal = !signalFilter || stock.signal === signalFilter;

      return matchesSearch && matchesSector && matchesSignal;
    });

    this.renderStocksGrid();
  }

  hideLoadingSpinner() {
    document.getElementById("loadingSpinner").style.display = "none";
  }

  showError(message) {
    const grid = document.getElementById("stocksGrid");
    grid.innerHTML = `
      <div class="col-12 text-center py-5">
        <i class="bi bi-exclamation-triangle display-1 text-danger"></i>
        <h4 class="mt-3 text-danger">Error Loading Data</h4>
        <p class="text-muted">${message}</p>
        <button class="btn btn-primary mt-2" onclick="stocksAnalysis.loadStocksData()">
          Try Again
        </button>
      </div>
    `;
  }

  formatNumber(num) {
    if (num >= 1e9) return (num / 1e9).toFixed(1) + "B";
    if (num >= 1e6) return (num / 1e6).toFixed(1) + "M";
    if (num >= 1e3) return (num / 1e3).toFixed(1) + "K";
    return num.toString();
  }
}

// Initialize stocks analysis when DOM is loaded
let stocksAnalysis;
document.addEventListener("DOMContentLoaded", () => {
  stocksAnalysis = new StocksAnalysis();
});

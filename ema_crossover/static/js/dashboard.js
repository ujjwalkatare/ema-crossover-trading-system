class Dashboard {
  constructor() {
    this.init();
  }

  init() {
    this.initSidebar();
    this.initNavigation();
    this.initMetrics();
  }

  initSidebar() {
    const sidebarToggle = document.querySelector(".sidebar-toggle");
    const sidebar = document.getElementById("sidebar");

    if (sidebarToggle && sidebar) {
      sidebarToggle.addEventListener("click", () => {
        sidebar.classList.toggle("show");
      });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener("click", (e) => {
      if (window.innerWidth < 992) {
        if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
          sidebar.classList.remove("show");
        }
      }
    });
  }

  initNavigation() {
    const navLinks = document.querySelectorAll(".sidebar-nav .nav-link");

    navLinks.forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();

        // Remove active class from all links
        navLinks.forEach((navLink) => navLink.classList.remove("active"));

        // Add active class to clicked link
        link.classList.add("active");

        // Show corresponding section
        this.showSection(link.getAttribute("href").substring(1));

        // Close sidebar on mobile after selection
        if (window.innerWidth < 992) {
          document.getElementById("sidebar").classList.remove("show");
        }
      });
    });
  }

  showSection(sectionId) {
    // Hide all sections
    document.querySelectorAll(".dashboard-section").forEach((section) => {
      section.classList.remove("active");
    });

    // Show selected section
    const targetSection = document.getElementById(sectionId);
    if (targetSection) {
      targetSection.classList.add("active");
    }
  }

  initMetrics() {
    // You can add metric animations or dynamic updates here
    console.log("Dashboard metrics initialized");
  }

  // Method to update metrics dynamically
  updateMetrics(data) {
    // Implementation for updating metrics with real data
  }

  // Method to handle responsive behavior
  handleResize() {
    const sidebar = document.getElementById("sidebar");
    if (window.innerWidth >= 992) {
      sidebar.classList.remove("show");
    }
  }
}

// Initialize dashboard when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  const dashboard = new Dashboard();

  // Handle window resize
  window.addEventListener("resize", () => {
    dashboard.handleResize();
  });
});

// Utility functions for the dashboard
const DashboardUtils = {
  formatCurrency: (amount) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
  },

  formatPercentage: (value) => {
    return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
  },

  formatNumber: (number) => {
    return new Intl.NumberFormat("en-US").format(number);
  },
};




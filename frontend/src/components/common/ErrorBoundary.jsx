import React from "react";

/**
 * AURA Error Boundary — Batch 3 Fix
 * Catches React component crashes and shows a friendly error UI
 * instead of a blank white screen. Wrap any major section with this.
 *
 * Usage:
 *   <ErrorBoundary section="Doctor Queue">
 *     <DoctorQueueComponent />
 *   </ErrorBoundary>
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error(`[AURA ErrorBoundary] Section: "${this.props.section || "Unknown"}" crashed:`, error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        React.createElement("div", {
          style: {
            display: "flex", flexDirection: "column", alignItems: "center",
            justifyContent: "center", padding: "40px 24px", margin: "16px",
            background: "#FFF7ED", border: "1.5px solid #FED7AA",
            borderRadius: "16px", textAlign: "center", minHeight: "200px"
          }
        },
          React.createElement("div", { style: { fontSize: "40px", marginBottom: "12px" } }, "\u26A0\uFE0F"),
          React.createElement("h3", {
            style: { fontSize: "16px", fontWeight: 700, color: "#92400E", margin: "0 0 8px 0" }
          }, this.props.section ? `${this.props.section} encountered an error` : "Something went wrong"),
          React.createElement("p", {
            style: { fontSize: "13px", color: "#78350F", margin: "0 0 20px 0", maxWidth: "320px", lineHeight: "1.5" }
          }, "This section failed to load. Your data is safe. Try retrying or refresh the page."),
          React.createElement("div", { style: { display: "flex", gap: "10px", flexWrap: "wrap", justifyContent: "center" } },
            React.createElement("button", {
              onClick: this.handleRetry,
              style: { padding: "8px 20px", background: "#D97706", color: "#fff", border: "none", borderRadius: "8px", fontWeight: 700, fontSize: "13px", cursor: "pointer" }
            }, "\uD83D\uDD04 Retry"),
            React.createElement("button", {
              onClick: () => window.location.reload(),
              style: { padding: "8px 20px", background: "#fff", color: "#92400E", border: "1.5px solid #FED7AA", borderRadius: "8px", fontWeight: 700, fontSize: "13px", cursor: "pointer" }
            }, "\u21BA Refresh Page")
          )
        )
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;

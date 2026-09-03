import re

filepath = r'c:\Users\shiva\Desktop\AAA\frontend\src\App.jsx'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add ErrorBoundary component class right before App component
error_boundary_code = '''class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("CRITICAL REACT RUNTIME ERROR CAUGHT BY BOUNDARY:", error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '40px', background: '#FEE2E2', border: '2px solid #DC2626', borderRadius: '16px', margin: '40px', color: '#991B1B', fontFamily: 'monospace', textAlign: 'left' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 800, marginBottom: '10px' }}>⚠️ React Runtime Exception Captured!</h2>
          <div style={{ fontSize: '15px', fontWeight: 700, marginBottom: '12px', background: '#FFFFFF', padding: '12px', borderRadius: '8px', border: '1px solid #FECACA' }}>
            {this.state.error && this.state.error.toString()}
          </div>
          <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '6px' }}>Component Stack Trace:</div>
          <pre style={{ fontSize: '12px', background: '#FFFFFF', padding: '16px', borderRadius: '8px', overflowX: 'auto', border: '1px solid #FECACA', color: '#0F172A' }}>
            {this.state.errorInfo && this.state.errorInfo.componentStack}
          </pre>
          <button onClick={() => { localStorage.clear(); window.location.reload(); }} style={{ marginTop: '16px', padding: '12px 24px', background: '#DC2626', color: '#FFFFFF', border: 'none', borderRadius: '10px', cursor: 'pointer', fontWeight: 700, fontSize: '14px' }}>
            Clear Cache & Reload Page 🔄
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function RootApp() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
'''

# Replace default export if present
if "export default App;" in content:
    content = content.replace("export default App;", error_boundary_code)
elif not "export default function RootApp" in content:
    content += "\n\n" + error_boundary_code

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("App.jsx ErrorBoundary injected successfully.")

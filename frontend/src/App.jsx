
function App() {
  return (
    <main>
      <h1>EGX Stock Analyzer</h1>

      <label htmlFor="stock-symbol">Stock Symbol</label>

      <input
        id="stock-symbol"
        name="stock-symbol"
        type="text"
        placeholder="e.g. EGAL"
      />

      <button type="button">Analyze</button>
    </main>
  );
}

export default App;
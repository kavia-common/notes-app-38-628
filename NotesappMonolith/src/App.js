import React, { useEffect, useState } from "react";
import "./App.css";
import { AuthProvider, useAuth } from "./AuthProvider";
import AuthPage from "./AuthPage";
import NotesDashboard from "./NotesDashboard";

function ThemedApp() {
  // Theme switching, persists in user preferences
  const [theme, setTheme] = useState('light');
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);
  useEffect(() => {
    if (window.localStorage.getItem("theme")) {
      setTheme(window.localStorage.getItem("theme"));
    }
  }, []);
  const setThemeAndStore = (t) => {
    setTheme(t);
    window.localStorage.setItem("theme", t);
  };

  const { token } = useAuth();

  return (
    <div className="App">
      <header className="App-header">
        <button className="theme-toggle"
          onClick={() => setThemeAndStore(theme === "light" ? "dark" : "light")}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === "light" ? "🌙 Dark" : "☀️ Light"}
        </button>
        <h1 style={{marginTop: "2rem"}}>Notes App</h1>
        <div style={{width: "100%", marginTop: "2rem"}}>
          {!token ? <AuthPage /> : <NotesDashboard />}
        </div>
      </header>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <ThemedApp />
    </AuthProvider>
  );
}
export default App;

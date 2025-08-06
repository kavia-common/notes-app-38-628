import React, { useRef, useState } from "react";
import { apiFetch } from "./api";
import { useAuth } from "./AuthProvider";

export default function AuthPage() {
    const { login } = useAuth();
    const [mode, setMode] = useState("login");
    const [error, setError] = useState(null);

    const usernameRef = useRef();
    const passwordRef = useRef();

    async function submit(e) {
        e.preventDefault();
        setError(null);
        const username = usernameRef.current.value.trim();
        const password = passwordRef.current.value.trim();
        try {
            if (mode === "login") {
                const data = await apiFetch("/auth/login", {
                    method: "POST",
                    body: { username, password }
                });
                login(data.token, data.user_id);
            } else {
                await apiFetch("/auth/register", {
                    method: "POST",
                    body: { username, password }
                });
                setMode("login");
            }
        } catch (err) {
            setError(err.message);
        }
    }

    return (
        <div>
            <form className="auth-form" onSubmit={submit} aria-label={mode === "login" ? "Login form" : "Register form"}>
                <h2>{mode === "login" ? "Login" : "Register"}</h2>
                <label>
                    Username
                    <input aria-required type="text" ref={usernameRef} />
                </label>
                <br />
                <label>
                    Password
                    <input aria-required type="password" ref={passwordRef} />
                </label>
                <br />
                {error && <div style={{color: "red"}}>{error}</div>}
                <button type="submit">{mode === "login" ? "Login" : "Register"}</button>
                <button type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}>
                    {mode === "login" ? "Need an account? Register" : "Have account? Login"}
                </button>
            </form>
        </div>
    );
}

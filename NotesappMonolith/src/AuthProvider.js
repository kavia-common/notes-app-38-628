import React, { createContext, useState, useContext } from "react";

const AuthContext = createContext();

export function useAuth() {
    return useContext(AuthContext);
}

// PUBLIC_INTERFACE
export function AuthProvider({ children }) {
    const stored = JSON.parse(localStorage.getItem("auth") || "{}");
    const [token, setToken] = useState(stored.token || null);
    const [userId, setUserId] = useState(stored.userId || null);

    const login = (token, userId) => {
        setToken(token);
        setUserId(userId);
        localStorage.setItem("auth", JSON.stringify({ token, userId }));
    };
    const logout = () => {
        setToken(null);
        setUserId(null);
        localStorage.removeItem("auth");
    };

    return (
        <AuthContext.Provider value={{ token, userId, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

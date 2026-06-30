import { createContext, useContext, useEffect, useState } from "react";
import { api, authApi } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(() => {
        if (typeof window === "undefined") return null;
        const raw = localStorage.getItem("lm_user");
        return raw ? JSON.parse(raw) : null;
    });
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const token = localStorage.getItem("lm_token");
        if (token && !user) {
            setLoading(true);
            authApi
                .me()
                .then((u) => {
                    setUser(u);
                    localStorage.setItem("lm_user", JSON.stringify(u));
                })
                .catch(() => {
                    localStorage.removeItem("lm_token");
                    localStorage.removeItem("lm_user");
                })
                .finally(() => setLoading(false));
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const persist = (token, u) => {
        localStorage.setItem("lm_token", token);
        localStorage.setItem("lm_user", JSON.stringify(u));
        // Dual-write to cookie for Next.js middleware
        document.cookie = `lm_token=${token}; path=/; max-age=86400; SameSite=Lax`;
        setUser(u);
    };

    const login = async (payload) => {
        const { access_token, user: u } = await authApi.login(payload);
        persist(access_token, u);
        return u;
    };

    const signup = async (payload) => {
        const { access_token, user: u } = await authApi.signup(payload);
        persist(access_token, u);
        return u;
    };

    const logout = async () => {
        // Call backend to blacklist the token (best-effort)
        try {
            await api.post("/auth/logout");
        } catch (e) {
            // Even if the request fails, clear local state
            console.warn("Logout API call failed:", e);
        } finally {
            localStorage.removeItem("lm_token");
            localStorage.removeItem("lm_user");
            // Clear cookie for Next.js middleware
            document.cookie = "lm_token=; path=/; max-age=0; SameSite=Lax";
            setUser(null);
        }
    };

    return (
        <AuthCtx.Provider value={{ user, loading, login, signup, logout }}>
            {children}
        </AuthCtx.Provider>
    );
}

export const useAuth = () => useContext(AuthCtx);

import { createContext, useContext, useEffect, useState } from "react";
import { authApi } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(() => {
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

    const logout = () => {
        localStorage.removeItem("lm_token");
        localStorage.removeItem("lm_user");
        setUser(null);
    };

    return (
        <AuthCtx.Provider value={{ user, loading, login, signup, logout }}>
            {children}
        </AuthCtx.Provider>
    );
}

export const useAuth = () => useContext(AuthCtx);

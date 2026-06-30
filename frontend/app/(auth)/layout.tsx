"use client";

import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "@/lib/auth";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <BrowserRouter>
      <AuthProvider>{children}</AuthProvider>
    </BrowserRouter>
  );
}

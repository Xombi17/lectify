import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Decode JWT payload without verifying signature (server-side check only)
// Signature verification happens server-side on API calls
function decodeToken(token: string): { sub?: string; role?: string } | null {
  try {
    const payload = token.split(".")[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

const PUBLIC_ROUTES = ["/", "/login", "/signup"];

const ROLE_ROUTES: Record<string, string> = {
  "/teacher": "teacher",
  "/student": "student",
  "/admin": "admin",
};

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Allow public routes
  if (PUBLIC_ROUTES.includes(pathname)) {
    return NextResponse.next();
  }

  // Get token from cookie
  const token = request.cookies.get("lm_token")?.value;

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Decode token to check role
  const payload = decodeToken(token);

  if (!payload) {
    // Invalid token — force re-login
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    const response = NextResponse.redirect(loginUrl);
    response.cookies.delete("lm_token");
    return response;
  }

  // Check role-based route access
  for (const [prefix, requiredRole] of Object.entries(ROLE_ROUTES)) {
    if (pathname.startsWith(prefix)) {
      if (payload.role !== requiredRole) {
        // Wrong role for this route — redirect to their dashboard
        const dashboards: Record<string, string> = {
          teacher: "/teacher/dashboard",
          student: "/student/dashboard",
          admin: "/admin/dashboard",
        };
        const redirect = dashboards[payload.role || ""] || "/";
        return NextResponse.redirect(new URL(redirect, request.url));
      }
      break;
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.svg).*)"],
};
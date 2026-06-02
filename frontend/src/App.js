import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/lib/auth";

import LandingPage from "@/pages/LandingPage";
import AuthPage from "@/pages/AuthPage";
import TeacherDashboard from "@/pages/TeacherDashboard";
import UploadLecturePage from "@/pages/UploadLecturePage";
import LectureDetailPage from "@/pages/LectureDetailPage";
import StudentDashboard from "@/pages/StudentDashboard";
import ReviewPage from "@/pages/ReviewPage";
import BookmarksPage from "@/pages/BookmarksPage";

import "@/App.css";

function RequireAuth({ role, children }) {
    const { user, loading } = useAuth();
    if (loading) return null;
    if (!user) return <Navigate to="/login" replace />;
    if (role && user.role !== role) {
        return <Navigate to={user.role === "teacher" ? "/teacher" : "/student"} replace />;
    }
    return children;
}

function HomeRedirect() {
    const { user } = useAuth();
    if (user) return <Navigate to={user.role === "teacher" ? "/teacher" : "/student"} replace />;
    return <LandingPage />;
}

export default function App() {
    return (
        <AuthProvider>
            <BrowserRouter>
                <Routes>
                    <Route path="/" element={<HomeRedirect />} />
                    <Route path="/login" element={<AuthPage mode="login" />} />
                    <Route path="/signup" element={<AuthPage mode="signup" />} />

                    <Route
                        path="/teacher"
                        element={
                            <RequireAuth role="teacher">
                                <TeacherDashboard />
                            </RequireAuth>
                        }
                    />
                    <Route
                        path="/teacher/upload"
                        element={
                            <RequireAuth role="teacher">
                                <UploadLecturePage />
                            </RequireAuth>
                        }
                    />
                    <Route
                        path="/teacher/lectures/:id"
                        element={
                            <RequireAuth role="teacher">
                                <LectureDetailPage />
                            </RequireAuth>
                        }
                    />

                    <Route
                        path="/student"
                        element={
                            <RequireAuth role="student">
                                <StudentDashboard />
                            </RequireAuth>
                        }
                    />
                    <Route
                        path="/student/lectures/:id"
                        element={
                            <RequireAuth role="student">
                                <LectureDetailPage />
                            </RequireAuth>
                        }
                    />
                    <Route
                        path="/student/review"
                        element={
                            <RequireAuth role="student">
                                <ReviewPage />
                            </RequireAuth>
                        }
                    />
                    <Route
                        path="/student/bookmarks"
                        element={
                            <RequireAuth role="student">
                                <BookmarksPage />
                            </RequireAuth>
                        }
                    />

                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </BrowserRouter>
            <Toaster
                position="top-right"
                toastOptions={{
                    classNames: {
                        toast: "border border-border bg-card text-foreground",
                    },
                }}
            />
        </AuthProvider>
    );
}

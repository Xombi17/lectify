import axios from "axios";

const BACKEND_URL =
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API });

api.interceptors.request.use((config) => {
    const token = localStorage.getItem("lm_token");
    if (token) {
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Response interceptor: handle 401 with token refresh
let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // If 401 and not a refresh/logout request and not already retried
        if (
            error.response?.status === 401 &&
            !originalRequest._retry &&
            !originalRequest.url?.includes("/auth/refresh") &&
            !originalRequest.url?.includes("/auth/logout")
        ) {
            if (isRefreshing) {
                // Queue this request until refresh completes
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                }).then((token) => {
                    originalRequest.headers.Authorization = `Bearer ${token}`;
                    return api(originalRequest);
                });
            }

            originalRequest._retry = true;
            isRefreshing = true;

            try {
                const response = await api.post("/auth/refresh");
                const { access_token } = response.data;
                localStorage.setItem("lm_token", access_token);
                originalRequest.headers.Authorization = `Bearer ${access_token}`;
                processQueue(null, access_token);
                return api(originalRequest);
            } catch (refreshError) {
                processQueue(refreshError, null);
                // Refresh failed — force logout
                localStorage.removeItem("lm_token");
                localStorage.removeItem("lm_user");
                window.location.href = "/auth";
                return Promise.reject(refreshError);
            } finally {
                isRefreshing = false;
            }
        }

        return Promise.reject(error);
    }
);

export const authApi = {
    signup: (data) => api.post("/auth/signup", data).then((r) => r.data),
    login: (data) => api.post("/auth/login", data).then((r) => r.data),
    me: () => api.get("/auth/me").then((r) => r.data),
};

export const lectureApi = {
    upload: (formData, onUploadProgress) =>
        api
            .post("/lectures", formData, {
                headers: { "Content-Type": "multipart/form-data" },
                onUploadProgress,
            })
            .then((r) => r.data),
    mine: () => api.get("/lectures/mine").then((r) => r.data),
    published: () => api.get("/lectures/published").then((r) => r.data),
    get: (id) => api.get(`/lectures/${id}`).then((r) => r.data),
    publish: (id) => api.post(`/lectures/${id}/publish`).then((r) => r.data),
    unpublish: (id) => api.post(`/lectures/${id}/unpublish`).then((r) => r.data),
    remove: (id) => api.delete(`/lectures/${id}`).then((r) => r.data),
    audioUrl: (id) => `${API}/lectures/${id}/audio`,
    submitQuiz: (id, answers) =>
        api.post(`/lectures/${id}/quiz/attempt`, { answers }).then((r) => r.data),
    translate: (id, target_language) =>
        api.post(`/lectures/${id}/translate`, { target_language }).then((r) => r.data),
    editMaterials: (id, patch) =>
        api.patch(`/lectures/${id}/materials`, patch).then((r) => r.data),
    pdfUrl: (id) => `${API}/lectures/${id}/pdf`,
};

export const bookmarkApi = {
    create: (payload) => api.post("/bookmarks", payload).then((r) => r.data),
    mine: () => api.get("/bookmarks/me").then((r) => r.data),
    forLecture: (id) => api.get(`/lectures/${id}/bookmarks`).then((r) => r.data),
    remove: (id) => api.delete(`/bookmarks/${id}`).then((r) => r.data),
};

export const reviewApi = {
    submit: (lecture_id, card_index, quality) =>
        api
            .post("/flashcards/review", { lecture_id, card_index, quality })
            .then((r) => r.data),
    due: () => api.get("/flashcards/due").then((r) => r.data),
    forLecture: (id) =>
        api.get(`/lectures/${id}/flashcards/state`).then((r) => r.data),
};

export const chatApi = {
    history: (lectureId) => api.get(`/lectures/${lectureId}/chat`).then((r) => r.data),
    ask: (lectureId, question) =>
        api.post(`/lectures/${lectureId}/chat`, { question }).then((r) => r.data),
};

export const searchApi = {
    search: (q, limit = 8) =>
        api.get("/search", { params: { q, limit } }).then((r) => r.data),
};

export const analyticsApi = {
    me: () => api.get("/analytics/me").then((r) => r.data),
};

// ============================================================================
// Phase 9 — AI Study Expansion API stubs
// ============================================================================
export const cheatsheetApi = {
    generate: (lectureId) => api.post(`/lectures/${lectureId}/cheatsheet`).then((r) => r.data),
};

export const podcastApi = {
    generate: (lectureId) => api.post(`/lectures/${lectureId}/podcast`).then((r) => r.data),
};

export const quizV2Api = {
    generate: (lectureId, opts) => api.post(`/lectures/${lectureId}/quiz-v2/generate`, opts).then((r) => r.data),
    submit: (lectureId, data) => api.post(`/lectures/${lectureId}/quiz-v2/submit`, data).then((r) => r.data),
};

export const conceptsV2Api = {
    generate: (lectureId) => api.post(`/lectures/${lectureId}/concepts-v2`).then((r) => r.data),
};

export const analyticsV2Api = {
    conceptMastery: () => api.get("/analytics/concept-mastery").then((r) => r.data),
    conceptMasteryForLecture: (lectureId) => api.get(`/analytics/concept-mastery/${lectureId}`).then((r) => r.data),
    streaks: () => api.get("/analytics/streaks").then((r) => r.data),
    goals: () => api.get("/analytics/goals").then((r) => r.data),
    searchConcepts: (q) => api.get("/search/concepts", { params: { q } }).then((r) => r.data),
};

// ============================================================================
// Admin API — Academic Hierarchy CRUD
// ============================================================================
export const adminApi = {
    // Institutions
    listInstitutions: () => api.get("/admin/institutions").then((r) => r.data),
    createInstitution: (data) => api.post("/admin/institutions", data).then((r) => r.data),
    getInstitution: (id) => api.get(`/admin/institutions/${id}`).then((r) => r.data),
    updateInstitution: (id, data) => api.put(`/admin/institutions/${id}`, data).then((r) => r.data),
    deleteInstitution: (id) => api.delete(`/admin/institutions/${id}`).then((r) => r.data),
    listInstitutionYears: (id) => api.get(`/admin/institutions/${id}/years`).then((r) => r.data),
    listInstitutionBranches: (id) => api.get(`/admin/institutions/${id}/branches`).then((r) => r.data),

    // Years
    listYears: () => api.get("/admin/years").then((r) => r.data),
    createYear: (data) => api.post("/admin/years", data).then((r) => r.data),
    getYear: (id) => api.get(`/admin/years/${id}`).then((r) => r.data),
    updateYear: (id, data) => api.put(`/admin/years/${id}`, data).then((r) => r.data),
    deleteYear: (id) => api.delete(`/admin/years/${id}`).then((r) => r.data),
    listYearSemesters: (id) => api.get(`/admin/years/${id}/semesters`).then((r) => r.data),

    // Branches
    listBranches: () => api.get("/admin/branches").then((r) => r.data),
    createBranch: (data) => api.post("/admin/branches", data).then((r) => r.data),
    getBranch: (id) => api.get(`/admin/branches/${id}`).then((r) => r.data),
    updateBranch: (id, data) => api.put(`/admin/branches/${id}`, data).then((r) => r.data),
    deleteBranch: (id) => api.delete(`/admin/branches/${id}`).then((r) => r.data),

    // Semesters
    listSemesters: () => api.get("/admin/semesters").then((r) => r.data),
    createSemester: (data) => api.post("/admin/semesters", data).then((r) => r.data),
    getSemester: (id) => api.get(`/admin/semesters/${id}`).then((r) => r.data),
    updateSemester: (id, data) => api.put(`/admin/semesters/${id}`, data).then((r) => r.data),
    deleteSemester: (id) => api.delete(`/admin/semesters/${id}`).then((r) => r.data),
    listSemesterSubjects: (id) => api.get(`/admin/semesters/${id}/subjects`).then((r) => r.data),
    listSemesterDivisions: (id) => api.get(`/admin/semesters/${id}/divisions`).then((r) => r.data),

    // Subjects
    listSubjects: () => api.get("/admin/subjects").then((r) => r.data),
    createSubject: (data) => api.post("/admin/subjects", data).then((r) => r.data),
    getSubject: (id) => api.get(`/admin/subjects/${id}`).then((r) => r.data),
    updateSubject: (id, data) => api.put(`/admin/subjects/${id}`, data).then((r) => r.data),
    deleteSubject: (id) => api.delete(`/admin/subjects/${id}`).then((r) => r.data),

    // Divisions
    listDivisions: () => api.get("/admin/divisions").then((r) => r.data),
    createDivision: (data) => api.post("/admin/divisions", data).then((r) => r.data),
    getDivision: (id) => api.get(`/admin/divisions/${id}`).then((r) => r.data),
    updateDivision: (id, data) => api.put(`/admin/divisions/${id}`, data).then((r) => r.data),
    deleteDivision: (id) => api.delete(`/admin/divisions/${id}`).then((r) => r.data),
    listDivisionClasses: (id) => api.get(`/admin/divisions/${id}/classes`).then((r) => r.data),

    // Classes
    listClasses: () => api.get("/admin/classes").then((r) => r.data),
    createClass: (data) => api.post("/admin/classes", data).then((r) => r.data),
    getClass: (id) => api.get(`/admin/classes/${id}`).then((r) => r.data),
    updateClass: (id, data) => api.put(`/admin/classes/${id}`, data).then((r) => r.data),
    deleteClass: (id) => api.delete(`/admin/classes/${id}`).then((r) => r.data),

    // Audit Logs
    listAuditLogs: () => api.get("/admin/audit-logs").then((r) => r.data),
};

// ============================================================================
// Teacher Assignment API (for admin dashboard)
// ============================================================================
export const assignmentApi = {
    assign: (data) => api.post("/enrollment/assignments", data).then((r) => r.data),
    listForClass: (classId) => api.get(`/enrollment/assignments/class/${classId}`).then((r) => r.data),
    listForTeacher: (teacherId) => api.get(`/enrollment/assignments/teacher/${teacherId}`).then((r) => r.data),
    remove: (assignmentId) => api.delete(`/enrollment/assignments/${assignmentId}`).then((r) => r.data),
};

// ============================================================================
// QR Code API (for admin dashboard)
// ============================================================================
export const qrApi = {
    generate: (classId) => api.post(`/qr/classes/${classId}/generate`).then((r) => r.data),
    regenerate: (classId) => api.post(`/qr/classes/${classId}/regenerate`).then((r) => r.data),
    get: (classId) => api.get(`/qr/classes/${classId}`).then((r) => r.data),
    downloadUrl: (classId, format = "svg") => `${API}/qr/classes/${classId}/download?format=${format}`,
    analytics: (classId) => api.get(`/qr/classes/${classId}/analytics`).then((r) => r.data),
    history: (classId) => api.get(`/qr/classes/${classId}/history`).then((r) => r.data),
};

// ============================================================================
// Enrollment API (for admin dashboard)
// ============================================================================
export const enrollmentApi = {
    listForClass: (classId) => api.get(`/enrollment/classes/${classId}/students`).then((r) => r.data),
};

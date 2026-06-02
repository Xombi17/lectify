import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
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

api.interceptors.response.use(
    (r) => r,
    (err) => {
        if (err?.response?.status === 401) {
            localStorage.removeItem("lm_token");
            localStorage.removeItem("lm_user");
        }
        return Promise.reject(err);
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

export const API_ROOT = process.env.REACT_APP_API_ROOT || "http://localhost:5000/api";

// HTTP utility for API calls with Auth and JSON
export async function apiFetch(path, {method = 'GET', body, token, headers, ...others} = {}) {
    headers = headers || {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (body && !(body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(body);
    }
    const resp = await fetch(API_ROOT + path, {method, body, headers, ...others});
    if (resp.status === 204) return null;
    if (!resp.ok) throw new Error((await resp.json()).message || "API error");
    return await resp.json();
}

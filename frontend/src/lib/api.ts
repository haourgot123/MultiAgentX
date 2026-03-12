import { useAuthStore } from "@/store/auth-store"

export const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

type ApiFetchOptions = RequestInit & {
    skipAuth?: boolean
}

export async function apiFetch<T = unknown>(
    path: string,
    options: ApiFetchOptions = {}
): Promise<T> {
    const { skipAuth = false, headers, body, ...restOptions } = options

    const finalHeaders = new Headers(headers || {})
    const isFormData = body instanceof FormData

    if (!isFormData && !finalHeaders.has("Content-Type")) {
        finalHeaders.set("Content-Type", "application/json")
    }

    if (!skipAuth) {
        const token = useAuthStore.getState().accessToken
        if (token) {
            finalHeaders.set("Token", token)
        }
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...restOptions,
        headers: finalHeaders,
        body,
    })

    if (!response.ok) {
        const errorPayload = await response.json().catch(() => null)
        const message =
            errorPayload?.message ||
            errorPayload?.detail ||
            `Request failed with status ${response.status}`
        throw new Error(message)
    }

    if (response.status === 204) {
        return undefined as T
    }

    return response.json() as Promise<T>
}

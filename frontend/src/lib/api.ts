import { useAuthStore } from "@/store/auth-store"

export const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"
export const SOCKET_BASE_URL =
    import.meta.env.VITE_SOCKET_BASE_URL || API_BASE_URL.replace(/\/api\/?$/, "")

type ApiFetchOptions = RequestInit & {
    skipAuth?: boolean
}

let refreshTokenPromise: Promise<boolean> | null = null

const refreshAccessToken = async (): Promise<boolean> => {
    if (refreshTokenPromise) {
        return refreshTokenPromise
    }

    const { refreshToken, refresh } = useAuthStore.getState()
    if (!refreshToken) {
        return false
    }

    refreshTokenPromise = refresh().finally(() => {
        refreshTokenPromise = null
    })
    return refreshTokenPromise
}

export async function apiFetch<T = unknown>(
    path: string,
    options: ApiFetchOptions = {}
): Promise<T> {
    const { skipAuth = false, headers, body, ...restOptions } = options

    const executeRequest = async (): Promise<Response> => {
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

        return fetch(`${API_BASE_URL}${path}`, {
            ...restOptions,
            headers: finalHeaders,
            body,
        })
    }

    let response = await executeRequest()

    if (!skipAuth && response.status === 401) {
        const refreshed = await refreshAccessToken()
        if (refreshed) {
            response = await executeRequest()
        }
    }

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

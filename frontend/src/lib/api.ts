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
        } else {
            // Unrecoverable 401 — clear auth state so ProtectedRoute redirects to login
            useAuthStore.setState({
                isAuthenticated: false,
                user: null,
                accessToken: null,
                refreshToken: null,
            })
            throw new Error("Session expired")
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

export type StreamEvent = {
    event: string
    data: any
}

export async function apiFetchStream(
    path: string,
    options: ApiFetchOptions = {},
    onEvent: (evt: StreamEvent) => void
): Promise<void> {
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
        } else {
            useAuthStore.setState({
                isAuthenticated: false,
                user: null,
                accessToken: null,
                refreshToken: null,
            })
            throw new Error("Session expired")
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

    if (!response.body) {
        throw new Error("No readable stream in response body")
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let done = false
    let buffer = ""

    while (!done) {
        const { value, done: doneReading } = await reader.read()
        done = doneReading
        if (value) {
            buffer += decoder.decode(value, { stream: true })

            // SSE messages are separated by double newlines
            let separatorIndex: number
            while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
                const rawEvent = buffer.slice(0, separatorIndex)
                buffer = buffer.slice(separatorIndex + 2)

                if (!rawEvent.trim()) continue

                const lines = rawEvent.split("\n")
                let eventType = "message"
                const dataLines: string[] = []

                for (const line of lines) {
                    if (line.startsWith("event:")) {
                        eventType = line.slice("event:".length).trim()
                    } else if (line.startsWith("data:")) {
                        dataLines.push(line.slice("data:".length).trim())
                    }
                }

                if (dataLines.length === 0) continue

                const dataStr = dataLines.join("\n")
                let parsed: any = dataStr
                try {
                    parsed = JSON.parse(dataStr)
                } catch {
                    // keep as raw string if not valid JSON
                }

                onEvent({ event: eventType, data: parsed })
            }
        }
    }
}

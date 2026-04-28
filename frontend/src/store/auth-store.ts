import { create } from "zustand"
import { persist } from "zustand/middleware"

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"

const apiUrl = (path: string) => `${API_BASE_URL}${path}`

/* ================= TYPES ================= */

interface User {
  id: number
  username: string
  fullName: string
  email: string
  dateOfBirth: string
  roles: string[]
  gender: string
  country: string
  phoneNumber: string
}

interface AuthState {
  hasHydrated: boolean
  isAuthenticated: boolean
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  setHasHydrated: (hydrated: boolean) => void

  login: (
    username: string,
    password: string,
  ) => Promise<boolean>
  register: (
    username: string,
    email: string,
    fullName: string,
    dateOfBirth: string,
    gender: string,
    country: string,
    phoneNumber: string,
    password: string,
    confirmPassword: string,
  ) => Promise<boolean>
  refresh: () => Promise<boolean>
  logout: () => Promise<void>
  changePassword: (
    oldPassword: string,
    newPassword: string,
    confirmPassword: string
  ) => Promise<{ success: boolean, message: string }>
  updateProfile: (
    fullName: string,
    dateOfBirth: string,
    gender: string,
    country: string,
    phoneNumber: string,
  ) => Promise<{ success: boolean, message: string }>
}

/* ================= STORE ================= */

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      /* ===== STATE ===== */
      hasHydrated: false,
      isAuthenticated: false,
      user: null,
      accessToken: null,
      refreshToken: null,
      setHasHydrated: (hydrated) => set({ hasHydrated: hydrated }),

      /* ===== UPDATE PROFILE ===== */
      updateProfile: async (fullName: string, dateOfBirth: string, gender: string, country: string, phoneNumber: string) => {
        try {
          const token = get().accessToken
          const userId = get().user?.id
          if (!(token && userId)) {
            return { success: false, message: "Not authenticated. Please login again." }
          }

          const res = await fetch(
            apiUrl(`/user/me/information?user_id=${userId}`),
            {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
                Token: token,
              },
              body: JSON.stringify({
                full_name: fullName,
                date_of_birth: dateOfBirth || null,
                gender,
                country,
                phone_number: phoneNumber,
              }),
            }
          )

          if (!res.ok) return { success: false, message: "Failed to update profile" }

          set((state) => ({
            user: state.user
              ? {
                  ...state.user,
                  fullName,
                  dateOfBirth,
                  gender,
                  country,
                  phoneNumber,
                }
              : state.user,
          }))
          return { success: true, message: "Profile updated successfully" }
        } catch {
          return { success: false, message: "Failed to update profile" }
        }
      },

      /* ===== REGISTER ===== */
      register: async (
        username: string,
        email: string,
        fullName: string,
        dateOfBirth: string,
        gender: string,
        country: string,
        phoneNumber: string,
        password: string
      ) => {
        try {
          const res = await fetch(
            apiUrl("/authentication/register"),
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                username,
                email,
                full_name: fullName,
                date_of_birth: dateOfBirth || null,
                gender,
                country,
                phone_number: phoneNumber,
                password,
              }),
            }
          )

          if (!res.ok) return false

          // Register endpoint returns UserResponse (no tokens).
          // Auto-login to obtain access & refresh tokens.
          return await get().login(username, password)
        } catch {
          return false
        }
      },
      /* ===== LOGIN ===== */
      login: async (username: string, password: string) => {
        try {
          const res = await fetch(
            apiUrl("/authentication/login"),
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ username, password }),
            }
          )

          if (!res.ok) return false

          const data = await res.json()
          // Mapping data
          const user = {
            id: data.user.id,
            username: data.user.username,
            fullName: data.user.full_name,
            email: data.user.email,
            dateOfBirth: data.user.date_of_birth,
            roles: data.user.roles,
            gender: data.user.gender,
            country: data.user.country,
            phoneNumber: data.user.phone_number,
          }
          set({
            isAuthenticated: true,
            user: user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
          })
          console.log("User:", user)
          return true
        } catch (err) {
          console.error("Login failed:", err)
          return false
        }
      },

      /* ===== CHANGE PASSWORD ===== */
    changePassword: async (oldPassword, newPassword, confirmPassword) => {
        if (newPassword !== confirmPassword) {
            return {
            success: false,
            message: "Password confirmation does not match",
            }
        }

        try {
            const token = get().accessToken
            if (!token) {
            return { success: false, message: "Not authenticated. Please login again." }
            }
            const userId = get().user?.id
            if (!userId) {
                return { success: false, message: "Not authenticated. Please login again." }
            }
            const res = await fetch(
            apiUrl(`/user/me/password?user_id=${userId}`),
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    Token: token,
                },
                body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword,
                }),
            }
            )

            if (!res.ok) {
            const errorData = await res.json().catch(() => null)

            return {
                success: false,
                message:
                errorData?.detail ||
                errorData?.message ||
                "Change password failed",
            }
            }

            return { success: true, message: "Password changed successfully" }
        } catch {
            return {
            success: false,
            message: "Network error. Please try again.",
            }
        }
    },


      /* ===== REFRESH TOKEN ===== */
      refresh: async () => {
        const refreshToken = get().refreshToken
        if (!refreshToken) {
          await get().logout()
          return false
        }

        try {
          const res = await fetch(
            apiUrl("/authentication/access"),
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({refresh_token: refreshToken }),
            }
          )

          if (!res.ok) {
            await get().logout()
            return false
          }

          const data = await res.json()
          const nextAccessToken = data.access_token
          if (!nextAccessToken) {
            await get().logout()
            return false
          }

          set({
            isAuthenticated: true,
            accessToken: nextAccessToken,
            refreshToken: data.refresh_token ?? refreshToken,
          })

          return true
        } catch (err) {
          console.error("Refresh failed:", err)
          await get().logout()
          return false
        }
      },

      /* ===== LOGOUT ===== */
      logout: async () => {
        try {
          const token = get().accessToken
          const userId = get().user?.id
          if (!(token && userId)) {
            console.error("Not authenticated. Please login again.")
            throw new Error("Not authenticated. Please login again.")
          }
          const res = await fetch(apiUrl(`/user/logout?user_id=${userId}`), {
            method: "POST",
            headers: {
              Token: token,
            },
          })
          if (!res.ok) {
            console.error("Logout failed. Please try again.")
          }
          console.log("Logout successful")
          set({
            isAuthenticated: false,
            user: null,
            accessToken: null,
            refreshToken: null,
          })
        } catch {
          console.warn("Logout API failed, force logout")
          set({
            isAuthenticated: false,
            user: null,
            accessToken: null,
            refreshToken: null,
          })
        }
      }
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      },
    }
  )
)

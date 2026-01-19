import { create } from "zustand"
import { persist } from "zustand/middleware"

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
  isAuthenticated: boolean
  user: User | null
  accessToken: string | null
  refreshToken: string | null

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
      isAuthenticated: false,
      user: null,
      accessToken: null,
      refreshToken: null,

      /* ===== UPDATE PROFILE ===== */
      updateProfile: async (fullName: string, dateOfBirth: string, gender: string, country: string, phoneNumber: string) => {
        try {
          const res = await fetch(
            "http://localhost:8000/api/user/me/information",
            {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ fullName, dateOfBirth, gender, country, phoneNumber }),
            }
          )

          if (!res.ok) return { success: false, message: "Failed to update profile" }

          const data = await res.json()
          set({ user: data.user })
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
        password: string,
        confirmPassword: string
      ) => {
        try {
          const res = await fetch(
            "http://localhost:8000/api/authentication/register",
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ username, email, fullName, dateOfBirth, gender, country, phoneNumber, password, confirmPassword }),
            }
          )

          if (!res.ok) return false

          const data = await res.json()
          set({
            isAuthenticated: true,
            user: data.user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
          })

          return true
        } catch {
          return false
        }
      },
      /* ===== LOGIN ===== */
      login: async (username: string, password: string) => {
        try {
          const res = await fetch(
            "http://localhost:8000/api/authentication/login",
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
            `http://localhost:8000/api/user/me/password?user_id=${userId}`,
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
        } catch (err) {
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
            "http://localhost:8000/api/authentication/refresh",
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
          set({ accessToken: data.accessToken })

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
          const res = await fetch(`http://localhost:8000/api/user/logout?user_id=${userId}`, {
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
        } catch (err) {
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
    }
  )
)

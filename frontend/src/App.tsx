import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import AppLayout from './layout/AppLayout'
import LoginPage from './pages/LoginPage'
import { ChatInterface } from './components/chat/ChatInterface'
import FilesPage from './pages/FilesPage'
import ChatWithFilePage from './pages/ChatWithFilePage'
import { ProtectedRoute } from './components/ProtectedRoute'
import { useAuthStore } from './store/auth-store'

function LoginRoute() {
  const { isAuthenticated } = useAuthStore()

  // If already logged in, redirect to home
  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <LoginPage />
}

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginRoute />
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <ChatInterface />
      },
      {
        path: 'files',
        element: <FilesPage />
      },
      {
        path: 'chat-file',
        element: <ChatWithFilePage />
      }
    ]
  }
])

function App() {
  return <RouterProvider router={router} />
}

export default App

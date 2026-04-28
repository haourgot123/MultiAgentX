import { Suspense, lazy } from 'react'
import { createBrowserRouter, RouterProvider} from 'react-router-dom'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Toaster } from "@/components/ui/sonner"

const AppLayout = lazy(() => import('./layout/AppLayout'))
const ChatInterface = lazy(() => import('./components/chat/ChatInterface').then((module) => ({ default: module.ChatInterface })))
const FilesPage = lazy(() => import('./pages/FilesPage'))
const ChatWithFilePage = lazy(() => import('./pages/ChatWithFilePage'))
const AgentSkillsPage = lazy(() => import('./pages/AgentSkillsPage'))
const VideoStudioPage = lazy(() => import('./pages/VideoStudioPage'))
const LoginPage = lazy(() => import('./store/LoginPage'))
const RegisterPage = lazy(() => import('./store/RegisterPage'))

function RouteFallback() {
  return (
    <div className="flex h-screen items-center justify-center bg-background text-sm text-text-muted">
      Loading...
    </div>
  )
}

function withSuspense(element: React.ReactNode) {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>
}


function LoginRoute() {
  return withSuspense(<LoginPage />)
}

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginRoute />
  },
  {
    path: '/register',
    element: withSuspense(<RegisterPage />)
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        {withSuspense(<AppLayout />)}
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: withSuspense(<ChatInterface />)
      },
      {
        path: 'files',
        element: withSuspense(<FilesPage />)
      },
      {
        path: 'chat-file',
        element: withSuspense(<ChatWithFilePage />)
      },
      {
        path: 'agent-skills',
        element: withSuspense(<AgentSkillsPage />)
      },
      {
        path: 'video',
        element: withSuspense(<VideoStudioPage />)
      }
    ]
  }
])

function App() {
  return (
    <>
      <RouterProvider router={router} />
      <Toaster />
    </>
  )
}

export default App

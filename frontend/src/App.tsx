import { createBrowserRouter, RouterProvider} from 'react-router-dom'
import AppLayout from './layout/AppLayout'
import { ChatInterface } from './components/chat/ChatInterface'
import FilesPage from './pages/FilesPage'
import ChatWithFilePage from './pages/ChatWithFilePage'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Toaster } from "@/components/ui/sonner"
import LoginPage from './store/LoginPage'


function LoginRoute() {
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
  return (
    <>
      <RouterProvider router={router} />
      <Toaster />
    </>
  )
}

export default App

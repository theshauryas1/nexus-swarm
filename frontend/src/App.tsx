// App.tsx — Master Onboarding Router Shell (Decide AI Style)

import { useEffect } from "react"
import { useNexusStore, getApiErrorMessage } from "./store/agentStore"
import { useAgentStream } from "./hooks/useAgentStream"
import { IntroPage } from "./components/pages/IntroPage"
import { LoginPage } from "./components/pages/LoginPage"
import { WorkspacePage } from "./components/pages/WorkspacePage"

export default function App() {
  const currentPage = useNexusStore((s) => s.currentPage)
  const navigate = useNexusStore((s) => s.navigate)
  const user = useNexusStore((s) => s.user)

  // Connect WebSocket
  useAgentStream()

  // Auto-routing guard: if user session exists and they go to login, route to IDE workspace automatically
  useEffect(() => {
    if (user && currentPage === "login") {
      navigate("ide")
    }
  }, [user, currentPage])

  // Load task from query param if present (?task=task_id)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlTaskId = params.get("task")
    if (urlTaskId) {
      const fetchPastTask = async () => {
        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        try {
          const res = await fetch(`${apiUrl}/status/${urlTaskId}`)
          if (!res.ok) {
            useNexusStore.getState().setApiError(await getApiErrorMessage(res))
            return
          }
          const taskData = await res.json()
          useNexusStore.getState().setTaskId(taskData.task_id, taskData.title)
          if (taskData.outputs) {
            const items = Object.entries(taskData.outputs).map(([agent, content]) => ({
              agent,
              pipeline: "system",
              type: agent,
              content: content as string
            }))
            useNexusStore.setState({ outputItems: items, taskRunning: false })
          }
          useNexusStore.getState().fetchFiles()
        } catch (e) {
          useNexusStore.getState().setApiError("Could not load the shared task. Check the backend connection.")
        }
      }
      fetchPastTask()
    }
  }, [])

  // Sync taskId to URL
  const taskId = useNexusStore(s => s.taskId)
  useEffect(() => {
    if (taskId) {
      const params = new URLSearchParams(window.location.search)
      if (params.get("task") !== taskId) {
        window.history.pushState({}, "", `?task=${taskId}`)
      }
    } else {
      // Clear query string if task is cleared
      const params = new URLSearchParams(window.location.search)
      if (params.has("task")) {
        window.history.pushState({}, "", window.location.pathname)
      }
    }
  }, [taskId])

  return (
    <>
      {currentPage === "intro" && <IntroPage />}
      {currentPage === "login" && <LoginPage />}
      {currentPage === "ide" && <WorkspacePage />}
    </>
  )
}

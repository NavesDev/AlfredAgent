import { BrowserRouter, Route, Routes } from 'react-router'
import { OverlayPage } from './features/assistant/pages/OverlayPage'
import { DashboardPage } from './features/dashboard/pages/DashboardPage'
import { ProjectPage } from './features/projects/pages/ProjectPage'
import { ProjectsPage } from './features/projects/pages/ProjectsPage'
import { SettingsPage } from './features/settings/pages/SettingsPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/overlay" element={<OverlayPage />} />
      </Routes>
    </BrowserRouter>
  )
}

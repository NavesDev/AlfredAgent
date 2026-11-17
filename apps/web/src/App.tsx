import { BrowserRouter, Route, Routes } from 'react-router'
import { DashboardPage } from './features/dashboard/pages/DashboardPage'
import { ProjectPage } from './features/projects/pages/ProjectPage'
import { ProjectsPage } from './features/projects/pages/ProjectsPage'
import { SettingsPage } from './features/settings/pages/SettingsPage'
import { OverlayPage } from './pages/OverlayPage'
import { ViewerPage } from './pages/ViewerPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/projects/:id" element={<ProjectPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/overlay" element={<OverlayPage />} />
        <Route path="/viewer" element={<ViewerPage />} />
      </Routes>
    </BrowserRouter>
  )
}

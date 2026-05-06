import { Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import LibraryPage from './pages/LibraryPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<LibraryPage />} />
      </Route>
    </Routes>
  )
}

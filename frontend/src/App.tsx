import { useState } from 'react'
import { UserProvider, useUser } from './context/UserContext'
import ChooseUser from './pages/ChooseUser'
import Home from './pages/Home'
import Discover from './pages/Discover'
import Recall from './pages/Recall'
import Admin from './pages/Admin'
import ErrorBoundary from './components/ErrorBoundary'

type Page = { name: 'home' } | { name: 'discover'; type?: string } | { name: 'recall' } | { name: 'admin' }

function AppContent() {
  const { currentUser } = useUser()
  const [page, setPage] = useState<Page>({ name: 'home' })

  if (!currentUser) {
    return <ChooseUser />
  }

  switch (page.name) {
    case 'discover':
      return (
        <Discover
          initialType={page.type}
          onBack={() => setPage({ name: 'home' })}
        />
      )
    case 'recall':
      return <Recall onBack={() => setPage({ name: 'home' })} />
    case 'admin':
      return <Admin onBack={() => setPage({ name: 'home' })} />
    default:
      return <Home onNavigate={(p: string, type?: string) => setPage({ name: p as any, type })} />
  }
}

function App() {
  return (
    <ErrorBoundary>
      <UserProvider>
        <AppContent />
      </UserProvider>
    </ErrorBoundary>
  )
}

export default App

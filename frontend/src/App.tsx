import { useState } from 'react'
import { UserProvider, useUser } from './context/UserContext'
import ChooseUser from './pages/ChooseUser'
import Home from './pages/Home'
import Discover from './pages/Discover'
import Recall from './pages/Recall'
import Admin from './pages/Admin'
import Watchlist from './pages/Watchlist'
import Profile from './pages/Profile'
import ErrorBoundary from './components/ErrorBoundary'

type Page =
  | { name: 'home' }
  | { name: 'discover'; type?: string; query?: string; genres?: string[] }
  | { name: 'recall'; query?: string }
  | { name: 'admin' }
  | { name: 'watchlist' }
  | { name: 'profile' }

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
          initialQuery={page.query}
          initialGenres={page.genres}
          onBack={() => setPage({ name: 'home' })}
        />
      )
    case 'recall':
      return <Recall initialQuery={page.query} onBack={() => setPage({ name: 'home' })} />
    case 'admin':
      return <Admin onBack={() => setPage({ name: 'home' })} />
    case 'watchlist':
      return <Watchlist onBack={() => setPage({ name: 'home' })} />
    case 'profile':
      return <Profile onBack={() => setPage({ name: 'home' })} />
    default:
      return <Home onNavigate={(p: string, opts?: { type?: string; query?: string; genres?: string[] }) => setPage({ name: p as any, ...opts })} />
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

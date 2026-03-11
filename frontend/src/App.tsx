import { useState } from 'react'
import { UserProvider, useUser } from './context/UserContext'
import ChooseUser from './pages/ChooseUser'
import Home from './pages/Home'
import Discover from './pages/Discover'

type Page = { name: 'home' } | { name: 'discover'; type?: string }

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
    default:
      return <Home onNavigate={(p: string, type?: string) => setPage({ name: p as any, type })} />
  }
}

function App() {
  return (
    <UserProvider>
      <AppContent />
    </UserProvider>
  )
}

export default App

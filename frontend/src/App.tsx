import { UserProvider, useUser } from './context/UserContext'
import ChooseUser from './pages/ChooseUser'
import Home from './pages/Home'

function AppContent() {
  const { currentUser } = useUser()

  if (!currentUser) {
    return <ChooseUser />
  }

  return <Home />
}

function App() {
  return (
    <UserProvider>
      <AppContent />
    </UserProvider>
  )
}

export default App

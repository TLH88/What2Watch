import { useEffect, useState } from 'react'

function App() {
  const [healthStatus, setHealthStatus] = useState<string>('checking...')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setHealthStatus(data.status))
      .catch(() => setHealthStatus('unreachable'))
  }, [])

  return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold">What2Watch</h1>
        <p className="text-gray-400">Media Discovery App</p>
        <div className="text-sm text-gray-500">
          Backend: <span className={healthStatus === 'ok' ? 'text-green-400' : 'text-red-400'}>{healthStatus}</span>
        </div>
      </div>
    </div>
  )
}

export default App

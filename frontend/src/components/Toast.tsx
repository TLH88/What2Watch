import { useState, useCallback } from 'react'

type ToastType = 'success' | 'error' | 'info'

interface ToastMessage {
  id: number
  text: string
  type: ToastType
}

let nextId = 0

export function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const show = useCallback((text: string, type: ToastType = 'success') => {
    const id = nextId++
    setToasts((prev) => [...prev, { id, text, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 5500)
  }, [])

  const success = useCallback((text: string) => show(text, 'success'), [show])
  const error = useCallback((text: string) => show(text, 'error'), [show])
  const info = useCallback((text: string) => show(text, 'info'), [show])

  return { toasts, success, error, info }
}

export function ToastContainer({ toasts }: { toasts: ToastMessage[] }) {
  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`px-4 py-2.5 rounded-xl text-sm font-medium shadow-xl animate-fade-in border ${
            t.type === 'success'
              ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20 shadow-emerald-500/5'
              : t.type === 'error'
                ? 'bg-red-500/10 text-red-300 border-red-500/20 shadow-red-500/5'
                : 'bg-amber-500/10 text-amber-300 border-amber-500/20 shadow-amber-500/5'
          }`}
          style={{ backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)' }}
        >
          {t.text}
        </div>
      ))}
    </div>
  )
}

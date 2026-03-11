import { useState, useRef, useCallback, useEffect } from 'react'

interface VoiceMicButtonProps {
  onTranscript: (text: string) => void
  disabled?: boolean
  className?: string
}

// Check browser support
const SpeechRecognition =
  (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

export default function VoiceMicButton({ onTranscript, disabled, className = '' }: VoiceMicButtonProps) {
  const [listening, setListening] = useState(false)
  const [supported] = useState(() => !!SpeechRecognition)
  const recognitionRef = useRef<any>(null)
  const transcriptRef = useRef('')

  const stop = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
      recognitionRef.current = null
    }
    setListening(false)
  }, [])

  const start = useCallback(() => {
    if (!SpeechRecognition || disabled) return

    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.interimResults = true
    recognition.continuous = true
    recognition.maxAlternatives = 1

    transcriptRef.current = ''

    recognition.onresult = (event: any) => {
      let final = ''
      let interim = ''
      for (let i = 0; i < event.results.length; i++) {
        const result = event.results[i]
        if (result.isFinal) {
          final += result[0].transcript
        } else {
          interim += result[0].transcript
        }
      }
      transcriptRef.current = final
      // Send interim + final so user sees live text
      onTranscript((final + interim).trim())
    }

    recognition.onerror = (event: any) => {
      if (event.error !== 'aborted') {
        console.warn('Speech recognition error:', event.error)
      }
      stop()
    }

    recognition.onend = () => {
      // Deliver final transcript
      if (transcriptRef.current.trim()) {
        onTranscript(transcriptRef.current.trim())
      }
      setListening(false)
      recognitionRef.current = null
    }

    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }, [disabled, onTranscript, stop])

  const toggle = useCallback(() => {
    if (listening) {
      stop()
    } else {
      start()
    }
  }, [listening, start, stop])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort()
      }
    }
  }, [])

  if (!supported) return null

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={disabled}
      title={listening ? 'Stop listening' : 'Voice input'}
      className={`flex items-center justify-center rounded-xl transition-colors disabled:opacity-50 ${
        listening
          ? 'bg-red-600 text-white animate-pulse'
          : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
      } ${className}`}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="currentColor"
        className="w-5 h-5"
      >
        {listening ? (
          // Stop icon
          <rect x="6" y="6" width="12" height="12" rx="2" />
        ) : (
          // Microphone icon
          <path d="M12 1a4 4 0 0 0-4 4v6a4 4 0 0 0 8 0V5a4 4 0 0 0-4-4Zm7 10a1 1 0 1 0-2 0 5 5 0 0 1-10 0 1 1 0 1 0-2 0 7 7 0 0 0 6 6.93V21h-3a1 1 0 1 0 0 2h8a1 1 0 1 0 0-2h-3v-3.07A7 7 0 0 0 19 11Z" />
        )}
      </svg>
    </button>
  )
}

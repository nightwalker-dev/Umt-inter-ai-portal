'use client'
import { useState, useEffect } from 'react'

export default function EventsPage() {
  const [events, setEvents] = useState([])
  const [error, setError] = useState('')
  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/events', {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail)
        setEvents(data)
      } catch (err: any) {
        setError(err.message)
      }
    }
    fetchEvents()
  }, [])

  return (
    <div className="p-8 text-black bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-4">Events</h1>
      {error && <div className="text-red-500 mb-4">{error}</div>}
      <ul className="space-y-4">
        {events.map((e: any) => (
          <li key={e.id} className="border p-4 rounded shadow">
            <h2 className="font-bold">{e.name}</h2>
            <p className="text-sm">{e.description}</p>
            <p className="text-xs text-gray-500">{e.start_date} to {e.end_date} - Status: {e.status}</p>
          </li>
        ))}
      </ul>
    </div>
  )
}

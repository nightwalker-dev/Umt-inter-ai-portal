'use client'
import { useState, useEffect } from 'react'

export default function EventsPage() {
  const [events, setEvents] = useState([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [newEvent, setNewEvent] = useState({ name: '', description: '', start_date: '', end_date: '', status: 'upcoming' })
  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

  useEffect(() => {
    fetchEvents()
  }, [])

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

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    try {
      const res = await fetch('http://localhost:8000/api/events', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newEvent)
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)

      setSuccess('Event created successfully')
      setNewEvent({ name: '', description: '', start_date: '', end_date: '', status: 'upcoming' })
      fetchEvents()
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="p-8 text-black bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-4">Events</h1>
      {error && <div className="text-red-500 mb-4 bg-red-100 p-2 rounded">{error}</div>}
      {success && <div className="text-green-800 mb-4 bg-green-100 p-2 rounded font-bold">{success}</div>}

      <div className="mb-8 p-4 border rounded bg-gray-50">
        <h2 className="font-bold mb-4">Create New Event (Admin Only)</h2>
        <form onSubmit={handleCreate} className="flex gap-4 flex-col max-w-lg">
          <div>
            <label className="block text-xs font-bold mb-1">Event Name</label>
            <input required type="text" value={newEvent.name} onChange={e => setNewEvent({...newEvent, name: e.target.value})} className="border p-2 rounded w-full" />
          </div>
          <div>
            <label className="block text-xs font-bold mb-1">Description</label>
            <textarea value={newEvent.description} onChange={e => setNewEvent({...newEvent, description: e.target.value})} className="border p-2 rounded w-full" />
          </div>
          <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-xs font-bold mb-1">Start Date</label>
                <input required type="date" value={newEvent.start_date} onChange={e => setNewEvent({...newEvent, start_date: e.target.value})} className="border p-2 rounded w-full" />
              </div>
              <div className="flex-1">
                <label className="block text-xs font-bold mb-1">End Date</label>
                <input required type="date" value={newEvent.end_date} onChange={e => setNewEvent({...newEvent, end_date: e.target.value})} className="border p-2 rounded w-full" />
              </div>
          </div>
          <div>
            <label className="block text-xs font-bold mb-1">Status</label>
            <select required value={newEvent.status} onChange={e => setNewEvent({...newEvent, status: e.target.value})} className="border p-2 rounded w-full">
              <option value="upcoming">Upcoming</option>
              <option value="ongoing">Ongoing</option>
              <option value="completed">Completed</option>
            </select>
          </div>
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded font-bold">Create Event</button>
        </form>
      </div>

      <ul className="space-y-4">
        {events.map((e: any) => (
          <li key={e.id} className="border p-4 rounded shadow">
            <h2 className="font-bold text-lg">{e.name}</h2>
            <p className="text-sm my-2">{e.description}</p>
            <p className="text-xs font-mono bg-gray-100 p-1 rounded inline-block">{e.start_date} to {e.end_date} - Status: <span className="font-bold">{e.status.toUpperCase()}</span></p>
          </li>
        ))}
      </ul>
    </div>
  )
}

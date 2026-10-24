'use client'

import { useState, useEffect } from 'react'

export default function AvailabilityPage() {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')
  const [freeQuery, setFreeQuery] = useState({ day: 'Monday', start: '09:00', end: '10:00' })
  const [freeMembers, setFreeMembers] = useState<any[]>([])

  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

  useEffect(() => {
    fetchAvailability()
  }, [])

  const fetchAvailability = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/availability', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      const result = await res.json()
      if (!res.ok) throw new Error(result.detail || "Failed to load")
      setData(result)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const checkWhoIsFree = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await fetch(`http://localhost:8000/api/availability/free?day=${freeQuery.day}&start_time=${freeQuery.start}&end_time=${freeQuery.end}`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      const result = await res.json()
      if (!res.ok) throw new Error(result.detail || "Failed to check")
      setFreeMembers(result)
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="p-8 text-black bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-4">Team Availability</h1>
      {error && <div className="text-red-500 mb-4">{error}</div>}

      {data && (
        <div className="mb-8">
          <h2 className="text-lg font-semibold mb-2">Members ({data.working_hours.start} - {data.working_hours.end})</h2>
          <div className="grid gap-4">
            {data.members.map((m: any) => (
              <div key={m.user_id} className="border p-4 rounded shadow-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-bold">{m.full_name} ({m.role})</span>
                  <span className={`px-2 py-1 text-xs rounded text-white ${m.timetable_status === 'saved' ? 'bg-green-600' : 'bg-red-600'}`}>
                    {m.timetable_status === 'saved' ? 'Timetable Saved' : 'Timetable Pending'}
                  </span>
                </div>
                {m.busy_slots.length > 0 ? (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {m.busy_slots.map((s: any, i: number) => (
                      <span key={i} className="bg-gray-200 text-xs px-2 py-1 rounded">
                        Busy: {s.day_of_week} {s.start_time}-{s.end_time}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 mt-2">No busy slots recorded.</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="border p-6 rounded bg-gray-50 max-w-lg">
        <h2 className="text-lg font-semibold mb-4">Who is free?</h2>
        <form onSubmit={checkWhoIsFree} className="flex flex-col gap-4">
          <div className="flex gap-4">
            <select value={freeQuery.day} onChange={e => setFreeQuery({...freeQuery, day: e.target.value})} className="border p-2 rounded flex-1">
              {['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map(d => <option key={d}>{d}</option>)}
            </select>
            <input type="time" value={freeQuery.start} onChange={e => setFreeQuery({...freeQuery, start: e.target.value})} className="border p-2 rounded" />
            <span className="self-center">to</span>
            <input type="time" value={freeQuery.end} onChange={e => setFreeQuery({...freeQuery, end: e.target.value})} className="border p-2 rounded" />
          </div>
          <button type="submit" className="bg-blue-600 text-white p-2 rounded font-bold">Check</button>
        </form>

        {freeMembers.length > 0 && (
          <div className="mt-4">
            <h3 className="font-bold mb-2">Free Members:</h3>
            <ul className="list-disc pl-5">
              {freeMembers.map((m: any) => <li key={m.user_id}>{m.full_name}</li>)}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

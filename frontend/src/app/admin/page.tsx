'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function AdminDashboard() {
  const [summary, setSummary] = useState<any>(null)
  const [error, setError] = useState('')
  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/dashboard', {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail)
        setSummary(data)
      } catch (err: any) {
        setError(err.message)
      }
    }
    fetchSummary()
  }, [])

  return (
    <div className="p-8 text-black bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-6">Dashboard Summary</h1>
      {error && <div className="text-red-500 mb-4 bg-red-100 p-2 rounded">{error}</div>}

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

          {summary.pending_reviews !== undefined && (
            <div className="border p-6 rounded shadow bg-blue-50">
              <h2 className="font-bold text-lg text-blue-800">Admin Actions</h2>
              <p className="text-3xl mt-2 font-bold">{summary.pending_reviews}</p>
              <p className="text-sm text-gray-600">Tasks waiting for review</p>
            </div>
          )}

          {summary.team_tasks_total !== undefined && (
            <div className="border p-6 rounded shadow bg-purple-50">
              <h2 className="font-bold text-lg text-purple-800">Team Progress</h2>
              <p className="text-3xl mt-2 font-bold">{summary.team_tasks_pending} <span className="text-lg text-gray-500">/ {summary.team_tasks_total}</span></p>
              <p className="text-sm text-gray-600">Pending tasks across team</p>
            </div>
          )}

          {summary.own_tasks_total !== undefined && (
            <div className="border p-6 rounded shadow bg-green-50">
              <h2 className="font-bold text-lg text-green-800">My Tasks</h2>
              <p className="text-3xl mt-2 font-bold">{summary.own_tasks_pending} <span className="text-lg text-gray-500">/ {summary.own_tasks_total}</span></p>
              <p className="text-sm text-gray-600">My pending tasks</p>
            </div>
          )}

          {summary.timetable_saved !== undefined && (
            <div className={`border p-6 rounded shadow ${summary.timetable_saved ? 'bg-green-50' : 'bg-red-50'}`}>
              <h2 className={`font-bold text-lg ${summary.timetable_saved ? 'text-green-800' : 'text-red-800'}`}>My Timetable</h2>
              <p className="text-xl mt-2 font-bold">{summary.timetable_saved ? 'Saved ✅' : 'Pending ❌'}</p>
            </div>
          )}

        </div>
      )}
    </div>
  )
}

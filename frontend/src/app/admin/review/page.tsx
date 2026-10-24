'use client'
import { useState, useEffect } from 'react'

export default function ReviewPage() {
  const [tasks, setTasks] = useState([])
  const [error, setError] = useState('')
  const [note, setNote] = useState('')
  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

  useEffect(() => {
    fetchTasks()
  }, [])

  const fetchTasks = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/tasks', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      // Only show completed tasks in review queue
      setTasks(data.filter((t: any) => t.status === 'completed'))
    } catch (err: any) {
      setError(err.message)
    }
  }

  const handleReview = async (taskId: string, status: string) => {
    if (status === 'rejected' && !note.trim()) {
        setError('A reason (note) is required to reject a task.')
        return
    }

    try {
      const res = await fetch(`http://localhost:8000/api/tasks/${taskId}/review`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ status, note: note || null })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)

      setNote('')
      setError('')
      fetchTasks()
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="p-8 text-black bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-4">Review Queue (Admin Only)</h1>
      {error && <div className="text-red-500 mb-4 bg-red-100 p-2 rounded">{error}</div>}

      <ul className="space-y-4">
        {tasks.map((t: any) => (
          <li key={t.id} className="border p-4 rounded shadow flex flex-col md:flex-row justify-between md:items-center">
            <div className="mb-4 md:mb-0">
              <h2 className="font-bold">{t.title}</h2>
              <p className="text-sm">Assigned To: {t.assigned_to.full_name}</p>
            </div>
            <div className="flex gap-2 items-center">
              <input
                type="text"
                placeholder="Rejection Reason"
                value={note}
                onChange={e => setNote(e.target.value)}
                className="border p-1 rounded"
              />
              <button onClick={() => handleReview(t.id, 'rejected')} className="bg-red-600 text-white px-3 py-1 rounded">Reject</button>
              <button onClick={() => handleReview(t.id, 'approved')} className="bg-green-600 text-white px-3 py-1 rounded">Approve</button>
            </div>
          </li>
        ))}
        {tasks.length === 0 && <p>No tasks waiting for review.</p>}
      </ul>
    </div>
  )
}

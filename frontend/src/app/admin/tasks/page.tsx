'use client'
import { useState, useEffect } from 'react'

export default function TasksPage() {
  const [tasks, setTasks] = useState([])
  const [error, setError] = useState('')
  const [users, setUsers] = useState([])
  const [events, setEvents] = useState([])
  const [newTask, setNewTask] = useState({ title: '', assigned_to: '', event_id: '' })
  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

  useEffect(() => {
    fetchTasks()
    fetchUsersAndEvents()
  }, [])

  const fetchTasks = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/tasks', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      setTasks(data)
    } catch (err: any) {
      setError(err.message)
    }
  }

  const fetchUsersAndEvents = async () => {
    try {
      const [uRes, eRes] = await Promise.all([
        fetch('http://localhost:8000/api/users', { headers: { 'Authorization': `Bearer ${getToken()}` }}),
        fetch('http://localhost:8000/api/events', { headers: { 'Authorization': `Bearer ${getToken()}` }})
      ])
      if (uRes.ok) setUsers(await uRes.json())
      if (eRes.ok) setEvents(await eRes.json())
    } catch (e) {
      console.error(e)
    }
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await fetch('http://localhost:8000/api/tasks', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            title: newTask.title,
            assigned_to: newTask.assigned_to,
            event_id: newTask.event_id || null
        })
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail)
      fetchTasks()
      setNewTask({ title: '', assigned_to: '', event_id: '' })
      setError('')
    } catch (err: any) {
      setError(err.message)
    }
  }

  const markComplete = async (taskId: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/tasks/${taskId}/complete`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      if (!res.ok) {
          const data = await res.json()
          throw new Error(data.detail)
      }
      fetchTasks()
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <div className="p-8 text-black bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-4">Tasks</h1>
      {error && <div className="text-red-500 mb-4 bg-red-100 p-2 rounded">{error}</div>}

      <div className="mb-8 p-4 border rounded bg-gray-50">
        <h2 className="font-bold mb-2">Create Task</h2>
        <form onSubmit={handleCreate} className="flex gap-2 items-center flex-wrap">
          <input required type="text" placeholder="Title" value={newTask.title} onChange={e => setNewTask({...newTask, title: e.target.value})} className="border p-2 rounded" />
          <select required value={newTask.assigned_to} onChange={e => setNewTask({...newTask, assigned_to: e.target.value})} className="border p-2 rounded">
            <option value="">Assign To...</option>
            {users.map((u: any) => <option key={u.id} value={u.id}>{u.full_name} ({u.role})</option>)}
          </select>
          <select value={newTask.event_id} onChange={e => setNewTask({...newTask, event_id: e.target.value})} className="border p-2 rounded">
            <option value="">No Event</option>
            {events.map((e: any) => <option key={e.id} value={e.id}>{e.name}</option>)}
          </select>
          <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded font-bold">Create</button>
        </form>
      </div>

      <ul className="space-y-4">
        {tasks.map((t: any) => (
          <li key={t.id} className="border p-4 rounded shadow flex justify-between items-center">
            <div>
              <h2 className="font-bold">{t.title}</h2>
              <p className="text-sm">Assigned To: {t.assigned_to.full_name}</p>
              <p className="text-xs text-gray-500">Status: {t.status}</p>
            </div>
            {t.status === 'pending' || t.status === 'rejected' ? (
                <button onClick={() => markComplete(t.id)} className="bg-green-600 text-white px-3 py-1 rounded">Mark Complete</button>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}

'use client'
import { useState, useEffect } from 'react'

export default function ActivityLogPage() {
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')
  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/activity', {
          headers: { 'Authorization': `Bearer ${getToken()}` }
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail)
        setLogs(data)
      } catch (err: any) {
        setError(err.message)
      }
    }
    fetchLogs()
  }, [])

  return (
    <div className="p-8 text-black bg-white min-h-screen">
      <h1 className="text-2xl font-bold mb-4">Activity Log (Admin Only)</h1>
      {error && <div className="text-red-500 mb-4 bg-red-100 p-2 rounded">{error}</div>}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse border text-sm">
          <thead>
            <tr className="bg-gray-200">
              <th className="border p-2">Timestamp</th>
              <th className="border p-2">Actor</th>
              <th className="border p-2">Action</th>
              <th className="border p-2">Entity</th>
              <th className="border p-2">Details</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log: any) => (
              <tr key={log.id}>
                <td className="border p-2">{new Date(log.created_at).toLocaleString()}</td>
                <td className="border p-2">{log.actor_id.full_name} ({log.actor_id.role})</td>
                <td className="border p-2 font-mono text-xs">{log.action}</td>
                <td className="border p-2">{log.entity_type} <span className="text-gray-500 text-xs">({log.entity_id})</span></td>
                <td className="border p-2">
                  <pre className="text-xs">{JSON.stringify(log.details, null, 2)}</pre>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {logs.length === 0 && !error && <p className="mt-4">No activity logs found.</p>}
      </div>
    </div>
  )
}

'use client'

import { useState, useEffect } from 'react'

export default function TimetablePage() {
  const [slots, setSlots] = useState<any[]>([])
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isDraft, setIsDraft] = useState(false)
  const [source, setSource] = useState('manual')
  const [isUploading, setIsUploading] = useState(false)

  const getToken = () => document.cookie.split('; ').find(row => row.startsWith('sb-access-token='))?.split('=')[1]
  // Check overlaps
  const checkOverlaps = (currentSlots: any[]) => {
    let warning = ''
    const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    for (const day of days) {
      const daySlots = currentSlots.filter(s => s.day_of_week === day).sort((a,b) => a.start_time.localeCompare(b.start_time))
      for (let i = 0; i < daySlots.length - 1; i++) {
        if (daySlots[i].end_time > daySlots[i+1].start_time) {
          warning = `Warning: Overlapping slots detected on ${day}.`
        }
      }
    }
    return warning
  }

  const [overlapWarning, setOverlapWarning] = useState('')

  useEffect(() => {
    setOverlapWarning(checkOverlaps(slots))
  }, [slots])


  useEffect(() => {
    fetchMyTimetable()
  }, [])

  const fetchMyTimetable = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/timetable/me', {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      const data = await res.json()
      if (res.ok && data.slots) {
        setSlots(data.slots)
        if (data.timetable) setSource(data.timetable.source)
      }
    } catch (err: any) {
      setError("Failed to fetch timetable")
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return
    const file = e.target.files[0]

    // Client side check max 5MB
    if (file.size > 5 * 1024 * 1024) {
      setError("File is too large (max 5MB)")
      return
    }

    setIsUploading(true)
    setError('')

    const formData = new FormData()
    formData.append('file', file)

    try {
      const res = await fetch('http://localhost:8000/api/timetable/extract', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${getToken()}` },
        body: formData
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Extraction failed")

      setSlots(data.draft_slots)
      setIsDraft(true)
      setSource('image')
      setSuccess("Extracted successfully! Please review before saving.")
    } catch (err: any) {
      setError(err.message)
      setSource('manual') // Fallback to manual
    } finally {
      setIsUploading(false)
    }
  }

  const addManualSlot = () => {
    setSlots([...slots, { day_of_week: 'Monday', start_time: '09:00', end_time: '10:00', subject: '', room: '' }])
    setIsDraft(true)
    setSource('manual')
  }

  const removeSlot = (index: number) => {
    const newSlots = [...slots]
    newSlots.splice(index, 1)
    setSlots(newSlots)
    setIsDraft(true)
  }

  const updateSlot = (index: number, field: string, value: string) => {
    const newSlots = [...slots]
    newSlots[index][field] = value
    setSlots(newSlots)
    setIsDraft(true)
  }

  const handleSave = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/timetable/me', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${getToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ source, slots })
      })

      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Failed to save")

      setSuccess("Timetable saved!")
      setIsDraft(false)
      setError('')
    } catch (err: any) {
      setError(err.message)
      setSuccess('')
    }
  }

  return (
    <div className="p-8 max-w-4xl mx-auto text-black bg-white">
      <h1 className="text-2xl font-bold mb-4">My Timetable</h1>

      {error && <div className="bg-red-100 text-red-700 p-2 mb-4 rounded">{error}</div>}
      {success && <div className="bg-green-100 text-green-700 p-2 mb-4 rounded">{success}</div>}
      {overlapWarning && <div className="bg-yellow-100 text-yellow-800 p-2 mb-4 rounded">{overlapWarning}</div>}

      <div className="mb-8 border p-4 rounded bg-gray-50">
        <h2 className="text-lg font-semibold mb-2">Upload Timetable Image</h2>
        <input
          type="file"
          accept="image/jpeg, image/png"
          onChange={handleFileUpload}
          disabled={isUploading}
        />
        {isUploading && <span className="ml-2 text-blue-600">Extracting...</span>}
        <p className="text-sm text-gray-500 mt-2">Max 5MB (JPG/PNG). Or use manual entry below if extraction fails.</p>
      </div>

      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">Weekly Slots {isDraft && <span className="text-orange-500 text-sm">(Draft)</span>}</h2>
        <button onClick={addManualSlot} className="bg-blue-600 text-white px-3 py-1 rounded">Add Slot Manually</button>
      </div>

      <div className="space-y-2 mb-6">
        {slots.length === 0 && <p className="text-gray-500 italic">No slots. Upload an image or add manually.</p>}
        {slots.map((s, i) => (
          <div key={i} className="flex gap-2 items-center border p-2 rounded">
            <select
              value={s.day_of_week}
              onChange={e => updateSlot(i, 'day_of_week', e.target.value)}
              className="border p-1 rounded"
            >
              {['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map(d => <option key={d}>{d}</option>)}
            </select>
            <input type="time" value={s.start_time} onChange={e => updateSlot(i, 'start_time', e.target.value)} className="border p-1 rounded" />
            <span>to</span>
            <input type="time" value={s.end_time} onChange={e => updateSlot(i, 'end_time', e.target.value)} className="border p-1 rounded" />
            <input type="text" placeholder="Subject" value={s.subject || ''} onChange={e => updateSlot(i, 'subject', e.target.value)} className="border p-1 rounded flex-1" />
            <input type="text" placeholder="Room" value={s.room || ''} onChange={e => updateSlot(i, 'room', e.target.value)} className="border p-1 rounded w-24" />
            <button onClick={() => removeSlot(i)} className="text-red-600 hover:text-red-800 font-bold px-2">X</button>
          </div>
        ))}
      </div>

      {slots.length > 0 && isDraft && (
        <button onClick={handleSave} className="bg-green-600 text-white px-4 py-2 rounded w-full font-bold">
          Save Timetable
        </button>
      )}
    </div>
  )
}

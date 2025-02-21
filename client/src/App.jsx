// client/src/App.jsx
import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [file, setFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState(null)

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setUploadProgress(0)
    setMessage('')
    setStatus(null)
  }

  const handleUpload = async () => {
    if (!file) return

    const formData = new FormData()
    formData.append('video', file)

    try {
      const response = await axios.post('http://localhost:5000/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setMessage(response.data.message)
      pollStatus(file.name)
    } catch (error) {
      console.error('Upload failed:', error)
      setMessage('Upload failed')
    }
  }

  const pollStatus = (filename) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`http://localhost:5000/status/${filename}`)
        setStatus(response.data)
        if (response.data.status === 'completed' || response.data.status === 'error') {
          clearInterval(interval)
        }
      } catch (error) {
        console.error('Status check failed:', error)
        clearInterval(interval)
      }
    }, 2000) // Poll every 2 seconds
  }

  return (
    <div style={{ padding: '20px' }}>
      <h1>Video Uploader</h1>
      <input
        type="file"
        accept="video/*,.mkv,video/x-matroska"
        onChange={handleFileChange}
      />
      <button onClick={handleUpload} disabled={!file}>
        Upload Video
      </button>
      {message && <p>{message}</p>}
      {status && (
        <div style={{ marginTop: '20px' }}>
          <p>Status: {status.status}</p>
          <p>Resolutions Available: {status.resolutions_available}/{status.total_resolutions}</p>
          {status.hls_master && (
            <p>HLS Stream: <a href={`http://localhost:5000/uploads/${status.hls_master}`}>{status.hls_master}</a></p>
          )}
        </div>
      )}
    </div>
  )
}

export default App
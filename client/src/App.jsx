// client/src/App.jsx
import { useState, useEffect } from 'react'
import axios from 'axios'

function App() {
  const [file, setFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0) // Network upload progress
  const [message, setMessage] = useState('')
  const [status, setStatus] = useState(null) // Server-side conversion status

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
        onUploadProgress: (progressEvent) => {
          const { loaded, total } = progressEvent
          const percent = Math.floor((loaded * 100) / total)
          setUploadProgress(percent)
        },
      })
      setMessage(response.data.message)
      setUploadProgress(100) // Ensure it hits 100% on completion
      pollStatus(file.name)
    } catch (error) {
      console.error('Upload failed:', error)
      setMessage('Upload failed')
      setUploadProgress(0)
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
      {uploadProgress > 0 && (
        <div style={{ marginTop: '20px' }}>
          <label>Upload Progress: {uploadProgress}%</label>
          <div
            style={{
              width: '100%',
              height: '20px',
              backgroundColor: '#e0e0e0',
              borderRadius: '4px',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                width: `${uploadProgress}%`,
                height: '100%',
                backgroundColor: '#4caf50',
                transition: 'width 0.3s ease-in-out',
              }}
            />
          </div>
        </div>
      )}
      {message && <p>{message}</p>}
      {status && (
        <div style={{ marginTop: '20px' }}>
          <p>Status: {status.status}</p>
          <p>Resolutions Available: {status.resolutions_available}/{status.total_resolutions}</p>
          {status.hls_master && (
            <p>
              HLS Stream:{' '}
              <a href={`http://localhost:5000/uploads/${status.hls_master}`}>
                {status.hls_master}
              </a>
            </p>
          )}
          {status.ffmpeg_progress && (
            <div>
              <h3>FFmpeg Conversion Progress:</h3>
              {Object.entries(status.ffmpeg_progress).map(([height, prog]) => (
                <div key={height}>
                  <p>
                    {height}p: {prog.status}
                  </p>
                  {prog.status === 'processing' && prog.progress.time && (
                    <p>Time Processed: {prog.progress.time}</p>
                  )}
                  {prog.status === 'processing' && prog.progress.frame && (
                    <p>Frames: {prog.progress.frame}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default App
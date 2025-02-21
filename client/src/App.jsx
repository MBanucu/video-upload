// client/src/App.jsx
import { useState } from 'react'
import axios from 'axios'

function App() {
  const [file, setFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setUploadProgress(0)
  }

  const handleUpload = async () => {
    if (!file) return

    const formData = new FormData()
    formData.append('video', file)

    try {
      const response = await axios.post('http://localhost:5000/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const { loaded, total } = progressEvent
          const percent = Math.floor((loaded * 100) / total)
          setUploadProgress(percent)
        },
      })
      console.log('Upload successful:', response.data)
      setUploadProgress(100)
    } catch (error) {
      console.error('Upload failed:', error)
      setUploadProgress(0)
    }
  }

  return (
    <div style={{ padding: '20px' }}>
      <h1>Video Uploader</h1>
      <input
        type="file"
        accept="video/*,.mkv,video/x-matroska,.MTS"
        onChange={handleFileChange}
      />
      <button onClick={handleUpload} disabled={!file}>
        Upload Video
      </button>

      {/* Progress Bar */}
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
    </div>
  )
}

export default App